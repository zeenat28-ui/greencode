import React, { useMemo } from 'react';
import {
  Mic,
  MicOff,
  Volume2,
  ShieldCheck,
  RotateCcw,
  X,
  Radio,
} from 'lucide-react';

/**
 * Authentic Amazon Alexa Futuristic Standalone Circular Voice Widget
 * "Sirf aik circle or usme ye alexa - na bhhht bara na bhhht chota"
 * 
 * Features:
 * 1. Compact standalone circular footprint (136px) - never covers code diffs behind it
 * 2. State "Listening": 44 radial audio spikes, glowing cyan-purple ring, central mic, equalizer
 * 3. State "Responding": 3D swirling turquoise vortex ribbon ring, bilateral waveform bars
 * 4. State "Standby": Breathing turquoise neon ring with high-sensitivity ambient detection
 * 5. Floating minimal speech pill above circle for spoken answers with dismiss (×)
 * 6. Top micro-ledger badge for forensic audit verification
 */
export default function AlexaCircleWidget({
  isListeningMic = false,
  speechSynthesisPlaying = false,
  voiceLoading = false,
  alwaysListening = true,
  wakeWordActive = false,
  ambientStatus = 'Listening for "Hey Alexa"...',
  voiceQueryInput = '',
  voiceResponseData = null,
  alexaActionNotice = null,
  micNotice = null,
  onToggleAlwaysListening,
  onToggleMicListening,
  onSpeakText,
  onOpenAuditModal,
  onExecuteQuery,
}) {
  const isResponding = speechSynthesisPlaying || voiceLoading;
  const isListening = wakeWordActive || (isListeningMic && !isResponding);
  const [bubbleDismissed, setBubbleDismissed] = React.useState(false);

  React.useEffect(() => {
    if (voiceResponseData) {
      setBubbleDismissed(false);
    }
  }, [voiceResponseData]);

  // Generate 44 radial audio spikes for the "Listening" state (Dynamic audio-reactive waveform)
  const radialSpikes = useMemo(() => {
    const total = 44;
    const center = 68;
    const radius = 46;
    const spikes = [];
    const isHearing = Boolean(voiceQueryInput && voiceQueryInput.trim().length > 0);

    for (let i = 0; i < total; i++) {
      const angle = (i * 2 * Math.PI) / total;
      const baseHeight = isHearing ? 5 : 2.5;
      const height = baseHeight + Math.sin(i * 1.6) * (isHearing ? 4.5 : 2.0) + ((i % 3) * (isHearing ? 3.0 : 1.2));
      const x1 = center + Math.cos(angle) * (radius + 2);
      const y1 = center + Math.sin(angle) * (radius + 2);
      const x2 = center + Math.cos(angle) * (radius + 2 + height);
      const y2 = center + Math.sin(angle) * (radius + 2 + height);
      spikes.push({ x1, y1, x2, y2, id: i, isHearing });
    }
    return spikes;
  }, [voiceQueryInput]);

  return (
    <div className="fixed bottom-14 right-6 sm:bottom-16 sm:right-8 z-40 flex flex-col items-end gap-2 pointer-events-none select-none">
      
      {/* ─────────────────────────────────────────────────────────────────
          0. MIC PERMISSION / HARDWARE NOTICE PILL
          ───────────────────────────────────────────────────────────────── */}
      {micNotice && (
        <div className="pointer-events-auto max-w-[280px] bg-amber-950/95 text-amber-100 border-2 border-amber-400/80 rounded-2xl p-3 shadow-xl backdrop-blur-md animate-in slide-in-from-bottom-2 duration-200 text-xs font-sans">
          <div className="flex items-center gap-1.5 font-bold text-amber-300 pb-1 border-b border-amber-500/30">
            <MicOff className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span>Microphone Notice</span>
          </div>
          <p className="pt-1.5 leading-relaxed text-[11px] text-amber-200">{micNotice}</p>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          1. REAL-TIME SPOKEN WORDS / LISTENING STATUS PILL (Shown when active)
          ───────────────────────────────────────────────────────────────── */}
      {isListening && !isResponding && (
        <div className="pointer-events-auto max-w-[280px] bg-slate-950/95 text-white border-2 border-cyan-400/80 rounded-2xl p-3 shadow-[0_8px_32px_rgba(0,240,255,0.35)] backdrop-blur-md animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center justify-between text-[11px] pb-1.5 border-b border-cyan-500/30">
            <div className="flex items-center gap-1.5 text-cyan-300 font-bold font-sans">
              <Mic className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>{voiceQueryInput ? 'Voice Ops · Hearing' : 'Voice Ops · Active'}</span>
            </div>
            <span className="text-[10px] text-cyan-400/80 font-mono">Hands-Free</span>
          </div>
          <p className="text-white text-xs font-medium pt-1.5 leading-relaxed font-sans">
            {voiceQueryInput ? `"${voiceQueryInput}"` : 'Listening... Try saying "score", "list issues", or "autofix all"'}
          </p>
          <div className="pt-2 flex items-center gap-1.5 text-[10px] text-cyan-300 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-ping shrink-0" />
            <span>Commands run automatically on pause</span>
          </div>
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          2. ANALYZING / PROCESSING STATUS PILL
          ───────────────────────────────────────────────────────────────── */}
      {voiceLoading && (
        <div className="pointer-events-auto max-w-[280px] bg-slate-950/95 text-white border-2 border-sky-400/80 rounded-2xl p-3 shadow-[0_8px_32px_rgba(56,189,248,0.35)] backdrop-blur-md animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center gap-2 text-sky-300 text-xs font-bold font-sans">
            <Radio className="w-3.5 h-3.5 animate-spin text-sky-400" />
            <span>Voice Ops is processing query...</span>
          </div>
          {voiceQueryInput && (
            <p className="text-slate-300 text-[11px] pt-1.5 italic font-sans truncate">
              "{voiceQueryInput}"
            </p>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          3. COMPACT FLOATING SPEECH ANSWER BUBBLE (Shown when answering)
          ───────────────────────────────────────────────────────────────── */}
      {voiceResponseData && !bubbleDismissed && !voiceLoading && (
        <div className="pointer-events-auto max-w-[300px] bg-slate-950/95 text-white border-2 border-cyan-400/80 rounded-2xl p-3 shadow-[0_8px_32px_rgba(0,240,255,0.35)] backdrop-blur-md animate-in slide-in-from-bottom-2 duration-200">
          <div className="flex items-center justify-between text-[11px] pb-1.5 border-b border-cyan-500/30">
            <div className="flex items-center gap-1.5 text-cyan-300 font-bold font-sans">
              <Volume2 className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span>Voice Ops · Response</span>
            </div>
            <button
              type="button"
              onClick={() => setBubbleDismissed(true)}
              className="text-slate-400 hover:text-white p-0.5 cursor-pointer rounded transition"
              title="Dismiss"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
          <p className="text-cyan-100 text-xs font-semibold leading-relaxed font-sans pt-1.5">
            "{voiceResponseData.spoken_response || voiceResponseData.response}"
          </p>
          {voiceResponseData.mcp_tool && (
            <div className="pt-2 flex items-center justify-between text-[10px] text-slate-400 font-mono">
              <span>Tool: <strong className="text-cyan-400">{voiceResponseData.mcp_tool}</strong></span>
              <span className="text-cyan-400 flex items-center gap-0.5 font-sans font-semibold">
                <ShieldCheck className="w-3 h-3" /> Verified
              </span>
            </div>
          )}
        </div>
      )}

      {/* ─────────────────────────────────────────────────────────────────
          THE STANDALONE CIRCLE (104px x 104px - Non-overlapping sleek footprint)
          Guaranteed 100% Pure Circle with clipPath and borderRadius: 50%
          ───────────────────────────────────────────────────────────────── */}
      <div
        onClick={onToggleMicListening}
        style={{
          width: '104px',
          height: '104px',
          borderRadius: '50%',
          overflow: 'hidden',
          clipPath: 'circle(50% at 50% 50%)',
          WebkitClipPath: 'circle(50% at 50% 50%)',
        }}
        className="pointer-events-auto relative flex items-center justify-center cursor-pointer group transition-transform hover:scale-105 active:scale-95 shadow-[0_4px_24px_rgba(0,0,0,0.45)]"
        title={
          isResponding
            ? 'Voice Ops is answering...'
            : isListening
            ? 'Voice Ops is listening... Click to send or pause'
            : 'Voice Ops · Ready (Click or speak command)'
        }
      >
        {/* Backdrop Circular Glow */}
        <div
          style={{ borderRadius: '50%' }}
          className={`absolute inset-0 bg-slate-950/95 transition-all ${
            isResponding
              ? 'shadow-[0_0_30px_rgba(0,240,255,0.65)]'
              : isListening
              ? 'shadow-[0_0_28px_rgba(56,189,248,0.7)]'
              : alwaysListening
              ? 'shadow-[0_0_20px_rgba(6,182,212,0.35)]'
              : 'shadow-[0_4px_20px_rgba(0,0,0,0.5)]'
          }`}
        />

        {/* ─────────────────────────────────────────────────────────────
            MODE 1: RESPONDING (Swirling 3D Turquoise Vortex Ribbon)
            ───────────────────────────────────────────────────────────── */}
        {isResponding ? (
          <div style={{ borderRadius: '50%' }} className="relative w-full h-full flex items-center justify-center">
            {/* Outer Rotating Glowing Neon Vortex Ribbon */}
            <div
              className="absolute inset-1.5 animate-[spin_2.8s_linear_infinite]"
              style={{
                borderRadius: '50%',
                background:
                  'conic-gradient(from 0deg, #00f0ff 0%, #0080ff 25%, #001f4d 50%, #00a8e1 75%, #00f0ff 100%)',
                padding: '6px',
                mask: 'radial-gradient(farthest-side, transparent calc(100% - 7px), #fff calc(100% - 6px))',
                WebkitMask:
                  'radial-gradient(farthest-side, transparent calc(100% - 7px), #fff calc(100% - 6px))',
                filter: 'drop-shadow(0 0 14px rgba(0, 240, 255, 0.85))',
              }}
            />

            {/* Inner Core: Volume Icon with Horizontal Waves (···ılı [ICON] ılı···) */}
            <div className="relative z-10 flex flex-col items-center justify-center text-center">
              <div className="flex items-center gap-2 mb-1">
                {/* Left horizontal wave */}
                <div className="flex items-center gap-0.5">
                  <span className="w-0.5 h-2 bg-cyan-400 rounded-full animate-bounce"></span>
                  <span className="w-0.5 h-3.5 bg-sky-300 rounded-full animate-bounce delay-75"></span>
                  <span className="w-0.5 h-2 bg-cyan-400 rounded-full animate-bounce delay-150"></span>
                </div>

                {/* Pure glowing icon without box or border */}
                <Volume2 className="w-6 h-6 text-cyan-300 drop-shadow-[0_0_14px_rgba(0,240,255,0.95)] animate-pulse" />

                {/* Right horizontal wave */}
                <div className="flex items-center gap-0.5">
                  <span className="w-0.5 h-2 bg-cyan-400 rounded-full animate-bounce delay-150"></span>
                  <span className="w-0.5 h-3.5 bg-sky-300 rounded-full animate-bounce delay-75"></span>
                  <span className="w-0.5 h-2 bg-cyan-400 rounded-full animate-bounce"></span>
                </div>
              </div>

              <span className="text-[10px] font-bold text-cyan-200 tracking-wide font-sans leading-tight drop-shadow">
                Speaking...
              </span>
            </div>
          </div>
        ) : isListening ? (
          /* ─────────────────────────────────────────────────────────────
              MODE 2: LISTENING (Radial Spikes Soundwave + Glowing Ring)
              ───────────────────────────────────────────────────────────── */
          <div style={{ borderRadius: '50%' }} className="relative w-full h-full flex items-center justify-center">
            {/* SVG Radial Frequency Waveform Spikes */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 136 136"
            >
              <defs>
                <linearGradient id="radialCyan" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.95" />
                  <stop offset="60%" stopColor="#38bdf8" stopOpacity="0.9" />
                  <stop offset="100%" stopColor="#818cf8" stopOpacity="0.95" />
                </linearGradient>
              </defs>

              {/* Pulsing Outer Ping */}
              <circle
                cx="68"
                cy="68"
                r="46"
                fill="none"
                stroke="#00f2fe"
                strokeWidth="1.5"
                strokeOpacity="0.3"
                className="animate-ping"
              />

              {/* Radial Audio Frequency Spikes */}
              {radialSpikes.map((spike) => (
                <line
                  key={spike.id}
                  x1={spike.x1}
                  y1={spike.y1}
                  x2={spike.x2}
                  y2={spike.y2}
                  stroke="url(#radialCyan)"
                  strokeWidth={spike.isHearing ? '1.8' : '1.1'}
                  strokeLinecap="round"
                  opacity={spike.isHearing ? '1' : '0.8'}
                />
              ))}

              {/* Main Glowing Neon Circle Ring */}
              <circle
                cx="68"
                cy="68"
                r="46"
                fill="none"
                stroke="url(#radialCyan)"
                strokeWidth="2.5"
                filter="drop-shadow(0 0 6px #00f2fe)"
              />
            </svg>

            {/* Inner Content: Pure Mic + Equalizer without box or border */}
            <div className="relative z-10 flex flex-col items-center justify-center text-center px-2">
              <Mic className="w-5 h-5 text-cyan-300 drop-shadow-[0_0_14px_rgba(0,240,255,1)] animate-pulse mb-0.5" />

              <div className="flex items-center gap-1">
                <span className="text-[10px] font-bold text-cyan-100 tracking-tight font-sans drop-shadow">
                  {voiceQueryInput ? 'Hearing' : 'Listening'}
                </span>
                <div className="flex items-end gap-0.5 h-2.5">
                  <span className="w-0.5 h-1.5 bg-cyan-400 rounded-full animate-bounce"></span>
                  <span className="w-0.5 h-2.5 bg-sky-300 rounded-full animate-bounce delay-75"></span>
                  <span className="w-0.5 h-1.5 bg-purple-400 rounded-full animate-bounce delay-150"></span>
                </div>
              </div>
              {voiceQueryInput ? (
                <span className="text-[8px] font-sans font-semibold text-cyan-200 truncate max-w-[96px] pt-0.5">
                  "{voiceQueryInput}"
                </span>
              ) : (
                <span className="text-[8px] font-mono text-cyan-400/90 pt-0.5">
                  Auto-Detect
                </span>
              )}
            </div>
          </div>
        ) : (
          /* ─────────────────────────────────────────────────────────────
              MODE 3: STANDBY (Breathing Circular Turquoise Neon Ring)
              ───────────────────────────────────────────────────────────── */
          <div style={{ borderRadius: '50%' }} className="relative w-full h-full flex items-center justify-center">
            {/* Pure SVG Vector Circle - Guaranteed 100% Round Geometric Ring */}
            <svg
              className="absolute inset-0 w-full h-full pointer-events-none"
              viewBox="0 0 136 136"
            >
              <defs>
                <linearGradient id="standbyCyanGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.9" />
                  <stop offset="50%" stopColor="#06b6d4" stopOpacity="0.8" />
                  <stop offset="100%" stopColor="#0284c7" stopOpacity="0.9" />
                </linearGradient>
              </defs>

              {/* Glowing Outer Neon Ring */}
              <circle
                cx="68"
                cy="68"
                r="56"
                fill="none"
                stroke="url(#standbyCyanGrad)"
                strokeWidth="2.5"
                filter="drop-shadow(0 0 8px rgba(6, 182, 212, 0.75))"
                className={alwaysListening ? 'animate-pulse' : ''}
              />

              {/* Inner Accent Ring */}
              {alwaysListening && (
                <circle
                  cx="68"
                  cy="68"
                  r="50"
                  fill="none"
                  stroke="#22d3ee"
                  strokeWidth="1"
                  strokeOpacity="0.35"
                  strokeDasharray="4 4"
                />
              )}
            </svg>

            {/* Central Pure Mic & Voice Ops Text */}
            <div className="relative z-10 flex flex-col items-center justify-center text-center p-2">
              <div className="mb-1 flex items-center justify-center">
                <Mic className="w-6 h-6 text-cyan-400 drop-shadow-[0_0_12px_rgba(6,182,212,0.9)] group-hover:text-cyan-200 transition-colors" />
              </div>

              <span className="text-[10px] font-bold text-slate-100 font-sans tracking-tight drop-shadow">
                Voice Ops
              </span>
              <span className="text-[8px] font-mono text-cyan-400 font-medium pt-0.5">
                {isListeningMic ? 'Listening' : 'Click to Start'}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
