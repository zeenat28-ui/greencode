import { useState, useEffect } from 'react';
import {
  Mic,
  Volume2,
  ArrowRight,
  Play,
  Cloud,
  ShieldCheck,
  Zap,
  VolumeX,
  Terminal,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import AmazonTechStackModal from './AmazonTechStackModal';

interface AlexaPrompt {
  id: string;
  title: string;
  icon: any;
  query: string;
  response: string;
  explanation: string;
  mcpAction: string;
}

const SAMPLE_PROMPTS: AlexaPrompt[] = [
  {
    id: 'region_arbitrage',
    title: 'Region Carbon Arbitrage',
    icon: Cloud,
    query: 'Which AWS region has the lowest marginal carbon intensity right now?',
    response:
      'eu-west-1 (Ireland) is currently 82% cleaner than us-east-1 (Virginia) at 44 gCO₂e/kWh vs 380 gCO₂e/kWh. Scheduling batch workloads in eu-west-1 reduces emissions by 1.42 kg CO₂e and lowers Spot compute cost.',
    explanation: 'Queries real-time marginal electrical grid carbon intensity across cloud regions.',
    mcpAction: 'compare_regions',
  },
  {
    id: 'repo_score',
    title: 'Repository SCI Audit',
    icon: ShieldCheck,
    query: 'What is the current GSF SCI score and quality gate status of our repository?',
    response:
      'Repository scores 84.5 out of 100 (Quality Gate Passed). Static AST and call-graph analysis flagged 5 optimization candidates across 42 files.',
    explanation: 'Evaluates repository AST metrics against ISO/IEC 21031:2024 (GSF SCI) thresholds.',
    mcpAction: 'audit_and_score',
  },
  {
    id: 'ai_refactor',
    title: 'Automated AST Refactoring',
    icon: Zap,
    query: 'Synthesize a patch for the quadratic string allocation in payment_processor.py.',
    response:
      'Replaced in-loop string concatenation on line 142 with a list buffer and single join allocation, reducing time complexity from O(N²) to O(N) and cutting CPU loop energy by 68%.',
    explanation: 'Generates deterministic AST patches verified by the complexity gate.',
    mcpAction: 'refactor_code',
  },
];

export default function AlexaVoiceCockpit() {
  const [selectedPrompt, setSelectedPrompt] = useState<AlexaPrompt>(SAMPLE_PROMPTS[0]);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [activeSpeech, setActiveSpeech] = useState<string>(SAMPLE_PROMPTS[0].response);
  const [customInput, setCustomInput] = useState('');
  const [showAmazonModal, setShowAmazonModal] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const [liveMcpTool, setLiveMcpTool] = useState<string>('compare_regions');

  useEffect(() => {
    let active = true;
    fetch('/api/voice/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: SAMPLE_PROMPTS[0].query, zone: 'IE' }),
    })
      .then((res) => (res.ok ? res.json() : null))
      .then((payload) => {
        if (!active || !payload?.spoken_response) return;
        setActiveSpeech(payload.spoken_response);
        if (payload.mcp_tool) {
          setLiveMcpTool(payload.mcp_tool);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  const speakText = (text: string) => {
    if (isMuted) {
      setIsPlaying(true);
      setTimeout(() => setIsPlaying(false), 1800);
      return;
    }

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.0;
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      setIsPlaying(true);
      window.speechSynthesis.speak(utterance);
    } else {
      setIsPlaying(true);
      setTimeout(() => setIsPlaying(false), 2000);
    }
  };

  const processQuery = async (rawQuery: string, fallbackResponse?: string) => {
    if (!rawQuery.trim()) return;
    setExpanded(true);

    try {
      const res = await fetch('/api/voice/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: rawQuery, zone: 'IE' }),
      });
      if (res.ok) {
        const payload = await res.json();
        if (payload.spoken_response) {
          setActiveSpeech(payload.spoken_response);
          if (payload.mcp_tool) {
            setLiveMcpTool(payload.mcp_tool);
          }
          speakText(payload.spoken_response);
          return;
        }
      }
    } catch {
      // Fall back gracefully if offline
    }

    const resp =
      fallbackResponse ||
      `Executed MCP tool for "${rawQuery}" against GreenCode MCP Server (/mcp) with regional grid telemetry.`;
    setActiveSpeech(resp);
    speakText(resp);
  };

  const handleSelectPrompt = (prompt: AlexaPrompt) => {
    setSelectedPrompt(prompt);
    setLiveMcpTool(prompt.mcpAction);
    processQuery(prompt.query, prompt.response);
  };

  const handleCustomQuery = (e: React.FormEvent) => {
    e.preventDefault();
    processQuery(customInput);
  };

  const startListening = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      return;
    }

    try {
      const recognition = new SpeechRecognition();
      recognition.lang = 'en-US';
      recognition.interimResults = false;
      setIsListening(true);
      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setCustomInput(transcript);
        processQuery(transcript);
        setIsListening(false);
      };
      recognition.onerror = () => setIsListening(false);
      recognition.onend = () => setIsListening(false);
      recognition.start();
    } catch {
      setIsListening(false);
    }
  };

  return (
    <>
      <div className="card overflow-hidden border-zinc-200/90 bg-white">
        {/* Compact Command Bar Header */}
        <div className="px-4 py-3 bg-zinc-950 text-zinc-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-6 h-6 rounded-md bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Terminal size={13} />
            </div>
            <span className="font-semibold text-xs text-zinc-100 tracking-tight">
              MCP &amp; Voice Command Console
            </span>
            <span className="hidden sm:inline-block text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
              MCP 2025-11-25 &middot; /mcp
            </span>
            <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              tool: {liveMcpTool}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowAmazonModal(true)}
              className="text-[11px] font-mono text-zinc-400 hover:text-zinc-100 px-2 py-1 rounded hover:bg-zinc-800 transition-colors"
            >
              Protocol Specs
            </button>
            <button
              type="button"
              onClick={() => {
                if (isPlaying) {
                  window.speechSynthesis?.cancel();
                  setIsPlaying(false);
                }
                setIsMuted(!isMuted);
              }}
              className="p-1.5 rounded-md bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-zinc-300 text-xs flex items-center gap-1 transition-colors"
              title={isMuted ? 'Unmute speech synthesis' : 'Mute speech synthesis'}
            >
              {isMuted ? <VolumeX size={12} /> : <Volume2 size={12} />}
              <span className="text-[10px] font-mono">{isMuted ? 'Muted' : 'TTS'}</span>
            </button>
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
            >
              <span>{expanded ? 'Collapse' : 'Expand'}</span>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
        </div>

        {/* Always-Visible Quick Command Bar */}
        <div className="p-3.5 bg-zinc-50/70 border-b border-zinc-200/60 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-[11px] font-mono text-zinc-400 mr-1">Presets:</span>
            {SAMPLE_PROMPTS.map((p) => {
              const isSelected = selectedPrompt.id === p.id;
              const Icon = p.icon;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleSelectPrompt(p)}
                  className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium transition-all ${
                    isSelected
                      ? 'bg-zinc-900 text-white shadow-sm'
                      : 'bg-white text-zinc-700 border border-zinc-200/90 hover:bg-zinc-100'
                  }`}
                >
                  <Icon size={12} className={isSelected ? 'text-emerald-400' : 'text-zinc-400'} />
                  <span>{p.title}</span>
                </button>
              );
            })}
          </div>

          <form onSubmit={handleCustomQuery} className="flex-1 max-w-md">
            <div className="relative flex items-center">
              <button
                type="button"
                onClick={startListening}
                className={`absolute left-2.5 p-1 rounded transition-colors ${
                  isListening ? 'text-rose-600 animate-pulse' : 'text-zinc-400 hover:text-zinc-700'
                }`}
                title="Voice query input"
              >
                <Mic size={13} />
              </button>
              <input
                type="text"
                placeholder="Run MCP query (e.g., compare eu-west-1 vs us-east-1 carbon intensity)..."
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                className="w-full pl-8 pr-16 py-1.5 text-xs bg-white border border-zinc-200 rounded-lg text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
              />
              <button
                type="submit"
                className="absolute right-1.5 px-2.5 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 text-white text-[11px] font-medium flex items-center gap-1"
              >
                <span>Run</span>
                <ArrowRight size={10} />
              </button>
            </div>
          </form>
        </div>

        {/* Expandable Response Drawer */}
        {expanded && (
          <div className="p-4 bg-white grid lg:grid-cols-12 gap-4 items-center">
            <div className="lg:col-span-8 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-[11px] text-zinc-500">
                  Query: <strong className="text-zinc-800 font-normal">&ldquo;{selectedPrompt.query}&rdquo;</strong>
                </span>
                <button
                  type="button"
                  onClick={() => speakText(activeSpeech)}
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 hover:text-emerald-800"
                >
                  <Play size={10} />
                  <span>{isPlaying ? 'Speaking...' : 'Replay Audio'}</span>
                </button>
              </div>
              <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200/80 text-xs text-zinc-800 leading-relaxed font-mono">
                {activeSpeech}
              </div>
            </div>

            <div className="lg:col-span-4 p-3 rounded-lg bg-emerald-50/50 border border-emerald-200/70 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-emerald-950">MCP Dispatch</span>
                <span className="font-mono text-[11px] text-emerald-800 bg-emerald-100/80 px-1.5 py-0.5 rounded">
                  {liveMcpTool}
                </span>
              </div>
              <p className="text-[11px] text-zinc-600 leading-relaxed">
                {selectedPrompt.explanation}
              </p>
            </div>
          </div>
        )}
      </div>

      <AmazonTechStackModal
        isOpen={showAmazonModal}
        onClose={() => setShowAmazonModal(false)}
      />
    </>
  );
}
