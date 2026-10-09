import { useState, useEffect } from 'react';
import { 
  Mic, Radio, Volume2, Sparkles, CheckCircle2, ArrowRight, 
  Play, Cloud, ShieldCheck, Zap, VolumeX, Info, Layers 
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
    title: 'Cloud Region Carbon Arbitrage',
    icon: Cloud,
    query: 'Alexa, ask GreenCode: which AWS region is cleanest for my job tonight?',
    response: 'Ireland (eu-west-1) is currently 82% cleaner than Virginia (us-east-1) at 44 gCO₂e/kWh vs 380 gCO₂e/kWh. Running your nightly ML job in Ireland saves 1.42 kg of CO₂ and cuts EC2 Spot costs.',
    explanation: 'Compares real-time electrical grid carbon intensity across AWS datacenters.',
    mcpAction: 'compare_regions (AWS Grid Telemetry)',
  },
  {
    id: 'repo_score',
    title: 'Repository Green Score',
    icon: ShieldCheck,
    query: 'Alexa, what is the green score of our repository?',
    response: 'Your repository scores 92 out of 100 (Grade A). Algorithmic efficiency meets Green Software Foundation guidelines with 0 critical energy bottlenecks.',
    explanation: 'Audits code efficiency against GSF Software Carbon Intensity (SCI v1.0) standards.',
    mcpAction: 'audit_and_score (Codebase Analysis)',
  },
  {
    id: 'ai_refactor',
    title: 'Amazon Bedrock AI Refactoring',
    icon: Zap,
    query: 'Alexa, ask GreenCode to optimize our PyTorch inference loop.',
    response: 'Detected unquantized FP32 tensors and missing inference mode. Amazon Bedrock generated an INT8 quantized loop, reducing memory bandwidth and cutting energy by 68%.',
    explanation: 'Synthesizes eco-refactored code using Amazon Bedrock (Claude 3.5 Sonnet).',
    mcpAction: 'refactor_code (Amazon Bedrock AI)',
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

  const speakText = (text: string) => {
    if (isMuted) {
      setIsPlaying(true);
      setTimeout(() => setIsPlaying(false), 2000);
      return;
    }

    if (typeof window !== 'undefined' && 'speechSynthesis' in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.05;
      utterance.pitch = 1.05; // Friendly voice timbre
      utterance.onend = () => setIsPlaying(false);
      utterance.onerror = () => setIsPlaying(false);
      setIsPlaying(true);
      window.speechSynthesis.speak(utterance);
    } else {
      setIsPlaying(true);
      setTimeout(() => setIsPlaying(false), 2400);
    }
  };

  const handleSelectPrompt = (prompt: AlexaPrompt) => {
    setSelectedPrompt(prompt);
    setActiveSpeech(prompt.response);
    speakText(prompt.response);
  };

  const processQuery = (rawQuery: string) => {
    if (!rawQuery.trim()) return;

    const q = rawQuery.toLowerCase();
    let resp = '';

    if (q.includes('ireland') || q.includes('virginia') || q.includes('region') || q.includes('clean') || q.includes('where') || q.includes('aws')) {
      resp = 'Ireland (eu-west-1) is currently 82% cleaner than Virginia (us-east-1). Deploying your batch jobs to eu-west-1 cuts carbon emissions by 1.42 kg and lowers Spot pricing.';
    } else if (q.includes('score') || q.includes('audit') || q.includes('green') || q.includes('sci')) {
      resp = 'Your codebase scored 92 out of 100 (Grade A). Algorithmic energy consumption complies with Green Software Foundation SCI standards.';
    } else if (q.includes('optimize') || q.includes('bedrock') || q.includes('fix') || q.includes('refactor') || q.includes('pytorch') || q.includes('loop')) {
      resp = 'Amazon Bedrock Claude 3.5 Sonnet analyzed the AST nodes and replaced inefficient quadratic loops with vectorized operations, reducing energy draw by 58%.';
    } else {
      resp = `Sample response for: "${rawQuery}". Through Alexa+, this query is routed to the live GreenCode MCP server (/mcp), which runs the real Bedrock and AWS Grid Telemetry tools.`;
    }

    setActiveSpeech(resp);
    speakText(resp);
  };

  const handleCustomQuery = (e: React.FormEvent) => {
    e.preventDefault();
    processQuery(customInput);
  };

  const startListening = () => {
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert("Microphone recognition is not supported in this browser. Please type your query in the input box.");
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
      <div className="card border-blue-200/90 bg-white overflow-hidden shadow-sm">
        {/* Top Banner with Amazon Qualification Badges */}
        <div className="bg-[#131921] text-white px-5 py-3 flex flex-wrap items-center justify-between gap-3 text-xs border-b border-[#232F3E]">
          <div className="flex items-center gap-2.5">
            <div className="w-6 h-6 rounded-full bg-[#00CAFF] flex items-center justify-center text-slate-950 shadow-sm">
              <Radio size={13} className="animate-pulse" />
            </div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-bold tracking-tight text-white text-sm">
                Amazon Alexa+ &amp; AWS Bedrock Voice Cockpit
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#00CAFF]/20 text-[#00CAFF] border border-[#00CAFF]/30">
                Voice MCP Agent &middot; Interactive Preview
              </span>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-[#FF9900]/20 text-[#FF9900] border border-[#FF9900]/30 font-mono">
                RFC 9728 Compliant
              </span>
            </div>
          </div>

          <div className="flex items-center gap-3 text-xs text-slate-300">
            <button
              onClick={() => setShowAmazonModal(true)}
              className="text-xs text-amber-300 hover:text-amber-200 flex items-center gap-1 font-semibold underline underline-offset-2"
            >
              <Info size={12} />
              AWS Tech Architecture
            </button>
            <span className="text-slate-600">|</span>
            <span
              className="flex items-center gap-1.5 font-medium"
              title="This in-browser cockpit speaks pre-authored sample responses; the deployed MCP server is reachable at /mcp"
            >
              <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
              <span className="text-amber-300">In-Browser Demo &middot; Live MCP at /mcp</span>
            </span>
          </div>
        </div>

        <div className="p-5 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
            <div>
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                Hands-Free Alexa Developer Experience
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-200 font-mono">
                  Live Spoken Audio
                </span>
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                Interact with GreenCode using your voice or presets. This preview speaks pre-authored
                sample responses in the browser; when asked through Alexa+, the same questions hit the
                live MCP server at <code className="font-mono text-[10px]">/mcp</code>:
              </p>
            </div>
            
            <div className="flex items-center gap-2">
              <button
                onClick={() => {
                  if (isPlaying) {
                    window.speechSynthesis?.cancel();
                    setIsPlaying(false);
                  }
                  setIsMuted(!isMuted);
                }}
                className={`p-1.5 rounded-lg border text-xs flex items-center gap-1.5 transition-all ${
                  isMuted 
                    ? 'bg-rose-50 border-rose-200 text-rose-700' 
                    : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                }`}
                title={isMuted ? 'Unmute voice' : 'Mute voice audio'}
              >
                {isMuted ? <VolumeX size={13} /> : <Volume2 size={13} />}
                <span className="text-[11px] font-medium">{isMuted ? 'Voice Muted' : 'Audio On'}</span>
              </button>
            </div>
          </div>

          {/* Two Column Layout: Prompts & Response */}
          <div className="grid lg:grid-cols-12 gap-5 items-start">
            {/* Left Column: Preset Voice Prompts */}
            <div className="lg:col-span-5 space-y-2.5">
              {SAMPLE_PROMPTS.map((p) => {
                const isSelected = selectedPrompt.id === p.id;
                const Icon = p.icon;
                return (
                  <button
                    key={p.id}
                    onClick={() => handleSelectPrompt(p)}
                    className={`w-full text-left p-3 rounded-xl border transition-all text-xs ${
                      isSelected
                        ? 'border-blue-500 bg-blue-50/70 ring-1 ring-blue-500/20 shadow-sm'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1.5">
                      <div className="flex items-center gap-1.5 font-bold text-slate-900">
                        <Icon size={14} className={isSelected ? 'text-blue-600' : 'text-slate-500'} />
                        <span>{p.title}</span>
                      </div>
                      <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full ${
                        isSelected ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-600'
                      }`}>
                        {isSelected ? 'Speaking' : 'Click to Speak'}
                      </span>
                    </div>
                    <p className="text-xs text-slate-700 font-medium italic">
                      &ldquo;{p.query}&rdquo;
                    </p>
                  </button>
                );
              })}

              {/* Custom Input with Real Microphone button */}
              <form onSubmit={handleCustomQuery} className="pt-1">
                <div className="relative flex items-center">
                  <input
                    type="text"
                    placeholder='Ask Alexa: "which AWS region is cleanest?"'
                    value={customInput}
                    onChange={(e) => setCustomInput(e.target.value)}
                    className="input pr-16 pl-9 text-xs py-2 bg-white w-full"
                  />
                  <button
                    type="button"
                    onClick={startListening}
                    className={`absolute left-2.5 p-1 rounded transition-colors ${
                      isListening ? 'text-rose-600 animate-pulse' : 'text-slate-400 hover:text-slate-600'
                    }`}
                    title="Speak into Microphone"
                  >
                    <Mic size={14} />
                  </button>
                  <button
                    type="submit"
                    className="absolute right-2 px-2 py-1 rounded bg-blue-600 hover:bg-blue-700 text-white text-[11px] font-medium flex items-center gap-1"
                    title="Ask Alexa"
                  >
                    <span>Ask</span>
                    <ArrowRight size={11} />
                  </button>
                </div>
                {isListening && (
                  <p className="text-[11px] text-rose-600 animate-pulse mt-1 pl-1">
                    Listening to your microphone... Speak your question now.
                  </p>
                )}
              </form>
            </div>

            {/* Right Column: Live Alexa Audio Response Box */}
            <div className="lg:col-span-7 rounded-xl bg-slate-50 border border-slate-200/90 p-4 space-y-3.5">
              {/* Audio Wave Header */}
              <div className="flex items-center justify-between pb-2.5 border-b border-slate-200">
                <div className="flex items-center gap-2">
                  <div className="w-7 h-7 rounded-full bg-blue-600 text-white flex items-center justify-center shadow-xs">
                    <Volume2 size={14} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-900">Alexa Spoken Response</p>
                    <p className="text-[11px] text-slate-500">Live Voice Output (Web Speech Synthesized)</p>
                  </div>
                </div>

                {/* Waveform indicator */}
                <div className="flex items-center gap-1 h-5 px-2 bg-white rounded-md border border-slate-200">
                  <span className={`w-1 bg-blue-600 rounded-full transition-all ${isPlaying ? 'voice-wave-1' : 'h-1'}`} />
                  <span className={`w-1 bg-blue-600 rounded-full transition-all ${isPlaying ? 'voice-wave-2' : 'h-2'}`} />
                  <span className={`w-1 bg-blue-600 rounded-full transition-all ${isPlaying ? 'voice-wave-3' : 'h-3'}`} />
                  <span className={`w-1 bg-blue-600 rounded-full transition-all ${isPlaying ? 'voice-wave-4' : 'h-2'}`} />
                  <span className={`w-1 bg-blue-600 rounded-full transition-all ${isPlaying ? 'voice-wave-5' : 'h-1'}`} />
                  <span className="text-[10px] font-mono text-slate-400 ml-1">
                    {isPlaying ? 'Speaking...' : 'Ready'}
                  </span>
                </div>
              </div>

              {/* Alexa Speech Bubble */}
              <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-semibold text-blue-700 flex items-center gap-1.5">
                    <Sparkles size={13} />
                    Alexa replied aloud:
                  </span>
                  <button
                    onClick={() => speakText(activeSpeech)}
                    className="text-[11px] text-blue-600 hover:text-blue-800 font-medium flex items-center gap-1"
                  >
                    <Play size={10} />
                    Replay Audio
                  </button>
                </div>
                <p className="text-xs text-slate-800 leading-relaxed font-normal">
                  {activeSpeech}
                </p>
              </div>

              {/* How it works note */}
              <div className="p-3 rounded-lg bg-blue-50/70 border border-blue-200/80 text-xs space-y-1">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="font-bold text-blue-950">Amazon Architecture Mapping:</span>
                  <span className="font-mono text-blue-800 font-semibold">{selectedPrompt.mcpAction}</span>
                </div>
                <p className="text-[11px] text-blue-900 leading-relaxed">
                  {selectedPrompt.explanation}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Amazon Ecosystem Architecture Proof Modal */}
      <AmazonTechStackModal
        isOpen={showAmazonModal}
        onClose={() => setShowAmazonModal(false)}
      />
    </>
  );
}
