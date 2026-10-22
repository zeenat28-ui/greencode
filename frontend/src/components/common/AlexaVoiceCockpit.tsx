import { useState, useEffect, useRef } from 'react';
import {
  ArrowRight,
  Cloud,
  ShieldCheck,
  Zap,
  Terminal,
  ChevronDown,
  ChevronUp,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import AmazonTechStackModal from './AmazonTechStackModal';
import { translateStatic as t } from '../../i18n/I18nContext';
import { authHeaders } from '../../services/api';

interface McpPreset {
  id: string;
  title: string;
  icon: any;
  query: string;
  zone: string;
}

/**
 * Example MCP queries. These are prompt shortcuts only - the answer always
 * comes from the live /api/voice/ask -> MCP tool call, never a hardcoded string.
 */
const MCP_PRESETS: McpPreset[] = [
  {
    id: 'region_arbitrage',
    title: t('alexa.presetTitles.regionArbitrage'),
    icon: Cloud,
    query: 'Which AWS region has the lowest marginal carbon intensity right now?',
    zone: 'IE',
  },
  {
    id: 'repo_score',
    title: t('alexa.presetTitles.repoScore'),
    icon: ShieldCheck,
    query: 'What is the current GSF SCI score and quality gate status of our repository?',
    zone: 'IE',
  },
  {
    id: 'ai_refactor',
    title: t('alexa.presetTitles.aiRefactor'),
    icon: Zap,
    query: 'Synthesize a patch for the quadratic string allocation in payment_processor.py.',
    zone: 'IE',
  },
];

export default function AlexaVoiceCockpit() {
  const [selectedPreset, setSelectedPreset] = useState<McpPreset>(MCP_PRESETS[0]);
  const [activeQuery, setActiveQuery] = useState<string>(MCP_PRESETS[0].query);
  const [activeZone, setActiveZone] = useState<string>(MCP_PRESETS[0].zone);
  const [answer, setAnswer] = useState<string | null>(null);
  const [mcpTool, setMcpTool] = useState<string>('compare_regions');
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [customInput, setCustomInput] = useState('');
  const [showAmazonModal, setShowAmazonModal] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const reqIdRef = useRef(0);

  const runQuery = async (rawQuery: string, zone: string) => {
    const trimmed = rawQuery.trim();
    if (!trimmed) return;
    setExpanded(true);
    setActiveQuery(trimmed);
    setActiveZone(zone);
    setStatus('loading');
    setAnswer(null);

    const reqId = ++reqIdRef.current;
    try {
      const res = await fetch('/api/voice/ask', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ query: trimmed, zone }),
      });
      const payload = res.ok ? await res.json() : null;
      // Ignore stale responses if a newer query was fired in the meantime.
      if (reqId !== reqIdRef.current) return;
      if (payload?.spoken_response) {
        setAnswer(payload.spoken_response);
        if (payload.mcp_tool) setMcpTool(payload.mcp_tool);
        setStatus('ready');
      } else {
        setStatus('error');
      }
    } catch {
      if (reqId !== reqIdRef.current) return;
      setStatus('error');
    }
  };

  useEffect(() => {
    runQuery(MCP_PRESETS[0].query, MCP_PRESETS[0].zone);
  }, []);

  const handleSelectPreset = (preset: McpPreset) => {
    setSelectedPreset(preset);
    runQuery(preset.query, preset.zone);
  };

  const handleCustomQuery = (e: React.FormEvent) => {
    e.preventDefault();
    runQuery(customInput, activeZone);
    setCustomInput('');
  };

  return (
    <>
      <div className="card overflow-hidden border-zinc-200/90 bg-white">
        {/* Command Bar Header */}
        <div className="px-4 py-3 bg-zinc-950 text-zinc-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="w-6 h-6 rounded-md bg-emerald-500/15 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
              <Terminal size={13} />
            </div>
            <span className="font-semibold text-xs text-zinc-100 tracking-tight">
               {t('alexa.queryConsole')}
            </span>
            <span className="hidden sm:inline-block text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-300 border border-zinc-700">
              MCP 2025-11-25 &middot; /mcp
            </span>
            <span className="hidden md:inline-flex items-center gap-1.5 text-[11px] font-mono text-emerald-400">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
              tool: {mcpTool}
            </span>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setShowAmazonModal(true)}
              className="text-[11px] font-mono text-zinc-400 hover:text-zinc-100 px-2 py-1 rounded hover:bg-zinc-800 transition-colors"
            >
              {t('alexa.protocolSpecs')}
            </button>
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="px-2.5 py-1 rounded-md bg-zinc-800 hover:bg-zinc-700 text-zinc-200 text-[11px] font-medium flex items-center gap-1 transition-colors"
            >
              <span>{expanded ? t('alexa.collapse') : t('alexa.expand')}</span>
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </button>
          </div>
        </div>

        {/* Query Bar: presets + free-form input */}
        <div className="p-3.5 bg-zinc-50/70 border-b border-zinc-200/60 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-1.5">
             <span className="text-[11px] font-mono text-zinc-400 mr-1">{t('alexa.presets')}</span>
            {MCP_PRESETS.map((p) => {
              const isSelected = selectedPreset.id === p.id;
              const Icon = p.icon;
              return (
                <button
                  key={p.id}
                  type="button"
                  onClick={() => handleSelectPreset(p)}
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
              <input
                type="text"
                 placeholder={t('alexa.placeholder')}
                value={customInput}
                onChange={(e) => setCustomInput(e.target.value)}
                className="w-full pl-3 pr-16 py-1.5 text-xs bg-white border border-zinc-200 rounded-lg text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
              />
              <button
                type="submit"
                disabled={!customInput.trim() || status === 'loading'}
                className="absolute right-1.5 px-2.5 py-1 rounded-md bg-zinc-900 hover:bg-zinc-800 text-white text-[11px] font-medium flex items-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                 <span>{t('alexa.run')}</span>
                <ArrowRight size={10} />
              </button>
            </div>
          </form>
        </div>

        {/* Response Drawer - always reflects the live MCP result or an honest state */}
        {expanded && (
          <div className="p-4 bg-white grid lg:grid-cols-12 gap-4 items-center">
            <div className="lg:col-span-8 space-y-1.5">
              <div className="flex items-center justify-between text-xs">
                <span className="font-mono text-[11px] text-zinc-500 truncate">
                  {t('alexa.queryLabel')} <span className="text-zinc-800 dark:text-zinc-200">&ldquo;{activeQuery}&rdquo;</span>
                  <span className="text-zinc-400"> &middot; zone: {activeZone}</span>
                </span>
              </div>
              {status === 'loading' && (
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200/80 text-xs text-zinc-500 flex items-center gap-2">
                  <Loader2 size={13} className="animate-spin text-zinc-400" />
                  <span>{t('alexa.dispatching')}</span>
                 </div>
               )}
               {status === 'error' && (
                 <div className="p-3 rounded-lg bg-rose-50 border border-rose-200/80 text-xs text-rose-700 flex items-start gap-2">
                   <AlertCircle size={13} className="mt-0.5 shrink-0" />
                   <span>
                     {t('alexa.error')}
                  </span>
                </div>
              )}
              {status === 'ready' && answer && (
                <div className="p-3 rounded-lg bg-zinc-50 border border-zinc-200/80 text-xs text-zinc-800 leading-relaxed font-mono">
                  {answer}
                </div>
              )}
            </div>

            <div className="lg:col-span-4 p-3 rounded-lg bg-emerald-50/50 border border-emerald-200/70 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="text-[11px] font-semibold text-emerald-950 dark:text-emerald-300">{t('alexa.mcpDispatch')}</span>
                <span className="font-mono text-[11px] text-emerald-800 bg-emerald-100/80 px-1.5 py-0.5 rounded">
                  {mcpTool}
                </span>
              </div>
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed"
                dangerouslySetInnerHTML={{ __html: t('alexa.mcpNote') }}
              />
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
