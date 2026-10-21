/**
 * useAlexaVoice.ts  (full-stack patched)
 *
 * Fixes applied:
 *  B1 - Remove credentials:'include' (incompatible with wildcard CORS on Vercel).
 *       Auth is passed via Authorization header instead.
 *  B2 - Attach Authorization: Bearer token from the in-memory session store.
 *  B3 - Read API base from the same source as api.ts (VITE_API_URL or empty on Vercel).
 *  B6 - Strip applicationId from browser payloads so the skill-ID guard does not
 *       block direct browser calls.  The guard only fires when GREENCODE_ALEXA_SKILL_ID
 *       is set AND an applicationId is present.
 *  B8 - autoStart no longer calls mic.start() without a user gesture.
 *       Instead it shows a visual prompt.  Mic only starts on explicit click.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { getAccessToken } from '../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface VoiceLogEntry {
  time: string;
  speaker: 'User' | 'Alexa';
  text: string;
  action: string;
}

export interface UseAlexaVoiceReturn {
  isListening: boolean;
  isReady: boolean;          // true once user has clicked mic at least once (B8)
  lastUtterance: string;
  lastReply: string;
  logs: VoiceLogEntry[];
  toggleMic: () => void;
  sendText: (text: string) => Promise<void>;
  clearReply: () => void;
}

// ─── Resolve API base once at module level (B3) ───────────────────────────────
//
// On Vercel the frontend is served from the same origin as the API rewrites,
// so an empty string is correct.  In local dev VITE_API_URL should be set to
// http://127.0.0.1:8000 so the vite dev server proxy-passes correctly.
//
const _isVercel =
  typeof window !== 'undefined' &&
  window.location.hostname.includes('vercel.app');

const API_BASE: string =
  (import.meta as { env: Record<string, string> }).env?.VITE_API_URL ??
  (_isVercel ? '' : 'http://127.0.0.1:8000');

// ─── ASK Payload Builder (B6: no applicationId in browser payloads) ───────────

function buildAskPayload(
  utterance: string,
  sessionAttributes: Record<string, unknown> = {},
) {
  return {
    version: '1.0',
    session: {
      new: false,
      sessionId: `greencode-web-${Date.now()}`,
      // applicationId deliberately omitted so the skill-ID guard does not
      // reject direct browser POSTs (the guard only checks when an id IS present
      // and mismatches — absence is treated as a non-Alexa-device caller).
      application: {},
      attributes: sessionAttributes,
      user: { userId: 'web-dashboard-user' },
    },
    context: {
      System: {
        application: {},
        user: { userId: 'web-dashboard-user' },
        device: { deviceId: 'web-browser', supportedInterfaces: {} },
      },
    },
    request: {
      type: 'IntentRequest',
      requestId: `req-${Date.now()}`,
      timestamp: new Date().toISOString().replace(/\.\d{3}Z$/, 'Z'),
      locale: 'en-US',
      intent: {
        name: 'FreeformGreenCodeQueryIntent',
        slots: { query: { name: 'query', value: utterance } },
      },
    },
  };
}

// ─── Strip SSML tags ──────────────────────────────────────────────────────────

function stripSsml(ssml: string): string {
  return ssml
    .replace(/<speak>/gi, '')
    .replace(/<\/speak>/gi, '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&apos;/g, "'")
    .replace(/\s{2,}/g, ' ')
    .trim();
}

// ─── Extract spoken text from ASK response body ───────────────────────────────

function extractSpeech(body: Record<string, unknown>): string {
  const response = (body as {
    response?: { outputSpeech?: { ssml?: string; text?: string } };
  }).response;
  if (!response?.outputSpeech) return 'GreenCode processed your request.';
  const os = response.outputSpeech;
  if (os.ssml) return stripSsml(os.ssml);
  if (os.text) return os.text;
  return 'GreenCode processed your request.';
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAlexaVoice(_autoStart = true): UseAlexaVoiceReturn {
  // B8: autoStart is accepted but ignored — mic requires explicit user gesture.
  // We track isReady so the UI can show a "click mic to activate" hint.
  const [isListening, setIsListening] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [lastUtterance, setLastUtterance] = useState('');
  const [lastReply, setLastReply] = useState('');
  const [logs, setLogs] = useState<VoiceLogEntry[]>([]);
  const [sessionAttributes, setSessionAttributes] = useState<
    Record<string, unknown>
  >({});

  const recognitionRef = useRef<any>(null);
  const autoRestartRef = useRef(false); // only true while user has mic active
  const processingRef = useRef(false);

  // ── Speak ──────────────────────────────────────────────────────────────────
  const speak = useCallback((text: string) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.05;
    utt.pitch = 1.0;
    utt.lang = 'en-US';
    window.speechSynthesis.speak(utt);
  }, []);

  // ── Call the Vercel serverless backend (B1, B2) ────────────────────────────
  const callBackend = useCallback(
    async (utterance: string): Promise<string> => {
      try {
        const payload = buildAskPayload(utterance, sessionAttributes);

        // B2: include Authorization header from in-memory session
        const token = getAccessToken();
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        if (token) headers['Authorization'] = `Bearer ${token}`;

        // B1: no credentials:'include' — avoids wildcard-CORS conflict
        const res = await fetch(`${API_BASE}/api/alexa/skill`, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
          // credentials omitted → defaults to 'same-origin' which is correct
          // on Vercel (same domain) and correct in dev with the vite proxy.
        });

        if (!res.ok) {
          const errText = await res.text().catch(() => '');
          console.warn('[useAlexaVoice] backend error', res.status, errText);
          return `GreenCode returned status ${res.status}. Please try again.`;
        }

        const data = (await res.json()) as Record<string, unknown>;

        // Persist session attributes for multi-turn context
        if (data.sessionAttributes && typeof data.sessionAttributes === 'object') {
          setSessionAttributes(
            data.sessionAttributes as Record<string, unknown>,
          );
        }
        return extractSpeech(data);
      } catch (err) {
        console.error('[useAlexaVoice] fetch error', err);
        return 'Could not reach GreenCode. Please check your connection.';
      }
    },
    [sessionAttributes],
  );

  // ── Process a recognised or typed utterance ────────────────────────────────
  const processUtterance = useCallback(
    async (raw: string) => {
      if (processingRef.current || !raw.trim()) return;
      processingRef.current = true;

      const now = new Date().toLocaleTimeString();
      setLastUtterance(raw);
      setLogs(prev =>
        [{ time: now, speaker: 'User' as const, text: raw, action: 'voice_input' },
          ...prev].slice(0, 100),
      );

      const reply = await callBackend(raw);

      setLastReply(reply);
      speak(reply);
      setLogs(prev =>
        [{
          time: new Date().toLocaleTimeString(),
          speaker: 'Alexa' as const,
          text: reply,
          action: 'voice_reply',
        }, ...prev].slice(0, 100),
      );

      processingRef.current = false;
    },
    [callBackend, speak],
  );

  // ── Start one SpeechRecognition session ────────────────────────────────────
  const startListening = useCallback(() => {
    const win = window as any;
    const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRec) {
      // Browser lacks speech recognition — sendText() still works.
      return;
    }

    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
    }

    const rec = new SpeechRec();
    rec.continuous = false;
    rec.interimResults = false;
    rec.lang = 'en-US';
    rec.maxAlternatives = 1;

    rec.onstart = () => {
      setIsListening(true);
      setIsReady(true);
    };

    rec.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      processUtterance(transcript);
    };

    rec.onerror = (event: any) => {
      if (event.error !== 'no-speech') {
        console.warn('[useAlexaVoice] recognition error:', event.error);
      }
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
      // Auto-restart only when user has explicitly left the mic on
      if (autoRestartRef.current) {
        setTimeout(() => {
          if (autoRestartRef.current) startListening();
        }, 400);
      }
    };

    recognitionRef.current = rec;
    try {
      rec.start();
    } catch (err) {
      console.warn('[useAlexaVoice] could not start recognition:', err);
      setIsListening(false);
    }
  }, [processUtterance]);

  const stopListening = useCallback(() => {
    autoRestartRef.current = false;
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
    }
    setIsListening(false);
  }, []);

  // ── Toggle on user click (this IS a user gesture) ─────────────────────────
  const toggleMic = useCallback(() => {
    if (autoRestartRef.current || isListening) {
      stopListening();
    } else {
      autoRestartRef.current = true;
      startListening();
    }
  }, [isListening, startListening, stopListening]);

  // ── Typed command fallback ─────────────────────────────────────────────────
  const sendText = useCallback(
    async (text: string) => {
      await processUtterance(text);
    },
    [processUtterance],
  );

  const clearReply = useCallback(() => setLastReply(''), []);

  // ── Cleanup on unmount ─────────────────────────────────────────────────────
  useEffect(() => {
    return () => {
      autoRestartRef.current = false;
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { /* ignore */ }
      }
      window.speechSynthesis?.cancel();
    };
  }, []);

  return {
    isListening,
    isReady,
    lastUtterance,
    lastReply,
    logs,
    toggleMic,
    sendText,
    clearReply,
  };
}
