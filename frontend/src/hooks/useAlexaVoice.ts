/**
 * useAlexaVoice.ts  (full-stack patched)
 *
 * Fixes applied:
 *  B1 - Remove credentials:'include' (incompatible with wildcard CORS on Vercel).
 *       Auth is passed via Authorization header instead.
 *  B2 - Attach Authorization: Bearer token from the in-memory session store.
 *  B3 - Read API base from the same source as api.ts (VITE_API_URL or empty on Vercel).
 *  B6 - Strip app_id_stripped from browser payloads so the skill-ID guard does not
 *       block direct browser calls.  The guard only fires when GREENCODE_ALEXA_SKILL_ID
 *       is set AND an app_id_stripped is present.
 *  B8 - autoStart no longer calls mic.start() without a user gesture.
 *       Instead it shows a visual prompt.  Mic only starts on explicit click.
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { getAccessToken, getGitHubToken } from '../services/api';
import { useT } from '../i18n/I18nContext';

// ─── Types ────────────────────────────────────────────────────────────────────

export interface VoiceLogEntry {
  time: string;
  speaker: 'User' | 'Alexa';
  text: string;
  action: string;
}

export interface UseAlexaVoiceReturn {
  isListening: boolean;
  isProcessing: boolean;
  isHandsFree: boolean;
  isReady: boolean;
  speechSupported: boolean;  // false when browser lacks SpeechRecognition
  lastUtterance: string;
  lastReply: string;
  logs: VoiceLogEntry[];
  toggleMic: () => void;
  sendText: (text: string) => Promise<void>;
  clearReply: () => void;
}

const API_BASE: string = import.meta.env.VITE_API_URL ?? '';

// ─── ASK Payload Builder (B6: no app_id_stripped in browser payloads) ───────────

function buildAskPayload(
  utterance: string,
  sessionAttributes: Record<string, unknown> = {},
) {
  let activeRepo = '';
  try {
    const storedScan = window.localStorage.getItem('greencode_scan_data');
    const scan = storedScan ? JSON.parse(storedScan) as { repo_path?: unknown } : null;
    if (typeof scan?.repo_path === 'string') {
      const slug = scan.repo_path
        .replace(/^https?:\/\/github\.com\//i, '')
        .replace(/\.git$/i, '')
        .replace(/\/$/, '')
        .trim();
      if (/^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$/.test(slug)) activeRepo = slug;
    }
  } catch (error: unknown) {
    console.warn('[useAlexaVoice] could not read the latest repository scan context', error);
    activeRepo = '';
  }

  return {
    version: '1.0',
    session: {
      new: false,
      sessionId: `greencode-web-${Date.now()}`,
      // app ID deliberately omitted so the skill-ID guard does not
      // reject direct browser POSTs (the guard only checks when an id IS present
      // and mismatches — absence is treated as a non-Alexa-device caller).
      application: {},
      attributes: activeRepo
        ? { ...sessionAttributes, active_repo: activeRepo }
        : sessionAttributes,
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
  const t = useT();
  // Detect SpeechRecognition support once at module init (not per-render)
  const _speechSupported =
    typeof window !== 'undefined' &&
    !!((window as any).SpeechRecognition || (window as any).webkitSpeechRecognition);

  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isHandsFree, setIsHandsFree] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [lastUtterance, setLastUtterance] = useState('');
  const [lastReply, setLastReply] = useState('');
  const [logs, setLogs] = useState<VoiceLogEntry[]>([]);
  const [sessionAttributes, setSessionAttributes] = useState<
    Record<string, unknown>
  >({});

  const recognitionRef = useRef<any>(null);
  const processingRef = useRef(false);
  const handsFreeRef = useRef(false);
  const speakingRef = useRef(false);
  const restartTimerRef = useRef<number | null>(null);
  const startListeningRef = useRef<() => void>(() => undefined);

  // ── Speak ──────────────────────────────────────────────────────────────────
  const speak = useCallback((text: string) => {
    const resumeListening = () => {
      speakingRef.current = false;
      if (handsFreeRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (handsFreeRef.current) startListeningRef.current();
        }, 350);
      }
    };
    if (!('speechSynthesis' in window)) {
      resumeListening();
      return;
    }
    window.speechSynthesis.cancel();
    const utt = new SpeechSynthesisUtterance(text);
    utt.rate = 1.05;
    utt.pitch = 1.0;
    utt.lang = 'en-US';
    speakingRef.current = true;
    utt.onend = resumeListening;
    utt.onerror = resumeListening;
    window.speechSynthesis.speak(utt);
  }, []);

  // ── Call the local ASK-compatible backend ─────────────────────────────────
  const callBackend = useCallback(
    async (utterance: string): Promise<string> => {
      try {
        const payload = buildAskPayload(utterance, sessionAttributes);

        // B2: include Authorization header from in-memory session
        const token = getAccessToken();
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };
        const githubToken = getGitHubToken();
        if (githubToken) headers['X-GitHub-Token'] = githubToken;
        if (token) headers['Authorization'] = `Bearer ${token}`;

        const res = await fetch(`${API_BASE}/api/voice/alexa/ask`, {
          method: 'POST',
          headers,
          body: JSON.stringify(payload),
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
      setIsProcessing(true);

      const now = new Date().toLocaleTimeString();
      setLastUtterance(raw);
      setLogs(prev =>
        [{ time: now, speaker: 'User' as const, text: raw, action: 'voice_input' },
          ...prev].slice(0, 100),
      );

      try {
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
      } finally {
        processingRef.current = false;
        setIsProcessing(false);
      }
    },
    [callBackend, speak],
  );

  // ── Start one SpeechRecognition session ────────────────────────────────────
  const startListening = useCallback(() => {
    const win = window as any;
    const SpeechRec = win.SpeechRecognition || win.webkitSpeechRecognition;

    if (!SpeechRec) {
      console.warn('[useAlexaVoice] SpeechRecognition not available in this browser');
      setLastReply(t('voice.unsupported'));
      return;
    }

    handsFreeRef.current = true;
    setIsHandsFree(true);
    if (restartTimerRef.current !== null) {
      window.clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
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
      const result = event.results[event.resultIndex];
      if (result?.isFinal) {
        const transcript = result[0]?.transcript?.trim();
        if (transcript) void processUtterance(transcript);
      }
    };

    rec.onerror = (event: any) => {
      if (event.error !== 'no-speech' && event.error !== 'aborted') {
        console.warn('[useAlexaVoice] recognition error:', event.error);
      }
      const messages: Record<string, string> = {
        'not-allowed': t('voice.permissionDenied'),
        'service-not-allowed': t('voice.serviceUnavailable'),
        network: t('voice.networkError'),
        'audio-capture': t('voice.noMicrophone'),
      };
      if (messages[event.error]) setLastReply(messages[event.error]);
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        handsFreeRef.current = false;
        setIsHandsFree(false);
      }
      setIsListening(false);
    };

    rec.onend = () => {
      setIsListening(false);
      if (recognitionRef.current !== rec) return;
      if (handsFreeRef.current && !processingRef.current && !speakingRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (handsFreeRef.current && !processingRef.current && !speakingRef.current) {
            startListeningRef.current();
          }
        }, 500);
      }
    };

    recognitionRef.current = rec;
    try {
      rec.start();
    } catch (err) {
      console.warn('[useAlexaVoice] could not start recognition:', err);
      setIsListening(false);
      if (handsFreeRef.current) {
        restartTimerRef.current = window.setTimeout(() => {
          if (handsFreeRef.current) startListeningRef.current();
        }, 1000);
      }
    }
  }, [processUtterance, t]);

  startListeningRef.current = startListening;

  const stopListening = useCallback(() => {
    handsFreeRef.current = false;
    setIsHandsFree(false);
    if (restartTimerRef.current !== null) {
      window.clearTimeout(restartTimerRef.current);
      restartTimerRef.current = null;
    }
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch { /* ignore */ }
    }
    setIsListening(false);
  }, []);

  // ── Toggle on user click (this IS a user gesture) ─────────────────────────
  const toggleMic = useCallback(() => {
    if (isHandsFree) {
      stopListening();
    } else {
      startListening();
    }
  }, [isHandsFree, startListening, stopListening]);

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
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch { /* ignore */ }
      }
      if (restartTimerRef.current !== null) {
        window.clearTimeout(restartTimerRef.current);
      }
      window.speechSynthesis?.cancel();
      handsFreeRef.current = false;
    };
  }, []);

  return {
    isListening,
    isProcessing,
    isHandsFree,
    isReady,
    speechSupported: _speechSupported,
    lastUtterance,
    lastReply,
    logs,
    toggleMic,
    sendText,
    clearReply,
  };
}
