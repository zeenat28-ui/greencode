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
import { callMcpTool, type McpToolResult } from '../../services/mcpClient';

interface GreenCodeEnvelope {
  status?: string;
  data?: Record<string, unknown>;
}

interface McpPreset {
  id: string;
  title: string;
  icon: any;
  query: string;
  zone: string;
  toolName: string;
  toolArguments: Record<string, unknown>;
}

const AUDIT_SAMPLE = `def build_report(items):
    result = ""
    for item in items:
        result += str(item)
    return result`;

const REFACTOR_SAMPLE = `def build_report(items):
    result = ""
    for item in items:
        result += str(item)
    return result`;

const MCP_PRESETS: McpPreset[] = [
  {
    id: 'region_arbitrage',
    title: t('alexa.presetTitles.regionArbitrage'),
    icon: Cloud,
    query: 'Compare Ireland, the Mid-Atlantic region, and Sweden grid carbon intensity',
    zone: 'IE',
    toolName: 'compare_regions',
    toolArguments: { zones: ['IE', 'US-MIDA-PJM', 'SE'] },
  },
  {
    id: 'repo_score',
    title: t('alexa.presetTitles.codeAudit'),
    icon: ShieldCheck,
    query: 'Audit the sample Python code and calculate its SCI score',
    zone: 'IE',
    toolName: 'audit_and_score',
    toolArguments: {
      source_code: AUDIT_SAMPLE,
      language: 'python',
      zone: 'IE',
      duration_seconds: 1,
    },
  },
  {
    id: 'ai_refactor',
    title: t('alexa.presetTitles.codeRefactor'),
    icon: Zap,
    query: 'Refactor the sample Python code and verify the behavior',
    zone: 'IE',
    toolName: 'refactor_code',
    toolArguments: {
      source_code: REFACTOR_SAMPLE,
      language: 'python',
      violation_type: 'quadratic_string_concatenation',
      guidance: 'Avoid repeated string allocation while preserving behavior.',
    },
  },
];

function toGreenCodeEnvelope(value: unknown): GreenCodeEnvelope | null {
  if (!value || typeof value !== 'object') return null;
  const record = value as Record<string, unknown>;
  if (record.result && typeof record.result === 'object') {
    return toGreenCodeEnvelope(record.result);
  }
  return typeof record.status === 'string' || record.data
    ? record as GreenCodeEnvelope
    : null;
}

function parseToolResult(result: McpToolResult): GreenCodeEnvelope | null {
  const structured = toGreenCodeEnvelope(result.structuredContent);
  if (structured) return structured;
  for (const item of result.content ?? []) {
    if (item.type !== 'text' || !item.text) continue;
    try {
      const parsed = toGreenCodeEnvelope(JSON.parse(item.text) as unknown);
      if (parsed) return parsed;
    } catch {
      continue;
    }
  }
  return null;
}

function formatToolResult(toolName: string, result: McpToolResult): string {
  const envelope = parseToolResult(result);
  if (!envelope) {
    return result.content?.map((item) => item.text).filter(Boolean).join('\n')
      || 'The MCP tool returned an empty result.';
  }

  const data = envelope.data ?? {};
  if (envelope.status === 'error') {
    const reason = data.reason;
    throw new Error(typeof reason === 'string' ? reason : 'The MCP tool reported an error.');
  }

  if (toolName === 'compare_regions') {
    const cleanest = data.cleanest as Record<string, unknown> | undefined;
    const dirtiest = data.dirtiest as Record<string, unknown> | undefined;
    if (cleanest && dirtiest) {
      return `Cleanest of the requested regions: ${cleanest.zone}, ${cleanest.carbon_intensity} gCO2e/kWh (${cleanest.tier}). Highest: ${dirtiest.zone}, ${dirtiest.carbon_intensity} gCO2e/kWh (${dirtiest.tier}).`;
    }
  }
  if (toolName === 'audit_and_score' || toolName === 'audit_code') {
    const energy = (data.energy ?? {}) as Record<string, unknown>;
    const measurement = energy.measurement_is_hardware === true
      ? 'hardware measurement'
      : `modelled estimate (${energy.measurement_method ?? 'method unavailable'})`;
    return `Code audit: score ${data.green_score ?? 'unavailable'}/100, grade ${data.grade ?? 'unavailable'}, ${data.violation_count ?? 'unknown'} findings. Energy basis: ${measurement}.`;
  }
  if (toolName === 'calculate_sci') {
    const sci = data.sci as Record<string, unknown> | undefined;
    const intensity = data.grid_intensity as Record<string, unknown> | undefined;
    return `SCI: ${sci?.sci_gco2_per_functional_unit ?? 'unavailable'} gCO2e per functional unit, grade ${data.grade ?? 'unavailable'}. Grid zone: ${intensity?.zone ?? 'not reported'}; energy input is modelled.`;
  }
  if (toolName === 'refactor_code') {
    const source = typeof data.source === 'string' ? data.source : 'unknown source';
    const provider = data.provider === 'aws_bedrock'
      ? 'Amazon Bedrock'
      : data.provider === 'google_gemini'
        ? 'Google Gemini'
        : data.provider === 'huggingface'
          ? 'Hugging Face'
          : typeof data.model === 'string'
            ? data.model
            : 'Deterministic rule engine';
    const verification = data.behaviour_verified === true
      ? 'behavior-verified'
      : source === 'fallback' || source === 'deterministic'
        ? 'rule-based proposal; not behavior-tested'
        : 'behavior verification not reported';
    const refactor = data.accepted === true
      ? `Accepted refactor proposal (${provider}; ${source}; ${verification}):\n${typeof data.refactored === 'string' ? data.refactored : 'No replacement code was returned.'}`
      : `The refactor was not accepted by verification (${data.reason ?? 'reason unavailable'}). No verified change is being presented.`;
    return refactor;
  }
  if (toolName === 'get_grid_intensity') {
    return data.carbon_intensity == null
      ? `Grid intensity is unavailable for ${data.zone ?? 'the requested zone'}. ${typeof data.unavailable_reason === 'string' ? data.unavailable_reason : ''}`.trim()
      : `${data.zone}: ${data.carbon_intensity} gCO2e/kWh. Source tier: ${data.intensity_source_tier ?? 'not reported'}${data.is_live === true ? ' (live source).' : ' (not confirmed live).'}`;
  }
  return JSON.stringify(envelope, null, 2);
}

export default function AlexaVoiceCockpit() {
  const [selectedPreset, setSelectedPreset] = useState<McpPreset>(MCP_PRESETS[0]);
  const [activeQuery, setActiveQuery] = useState<string>(MCP_PRESETS[0].query);
  const [activeZone, setActiveZone] = useState<string>(MCP_PRESETS[0].zone);
  const [answer, setAnswer] = useState<string | null>(null);
  const [mcpTool, setMcpTool] = useState<string>('connecting');
  const [status, setStatus] = useState<'idle' | 'loading' | 'ready' | 'error'>('loading');
  const [customInput, setCustomInput] = useState('');
  const [showAmazonModal, setShowAmazonModal] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const reqIdRef = useRef(0);

  const runQuery = async (
    rawQuery: string,
    zone: string,
    toolName: string,
    toolArguments: Record<string, unknown>,
  ) => {
    const trimmed = rawQuery.trim();
    if (!trimmed) return;
    setExpanded(true);
    setActiveQuery(trimmed);
    setActiveZone(zone);
    setStatus('loading');
    setAnswer(null);

    const reqId = ++reqIdRef.current;
    try {
      const result = await callMcpTool(toolName, toolArguments);
      // Ignore stale responses if a newer query was fired in the meantime.
      if (reqId !== reqIdRef.current) return;
      setAnswer(formatToolResult(toolName, result));
      setMcpTool(toolName);
      setStatus('ready');
    } catch (error) {
      if (reqId !== reqIdRef.current) return;
      setAnswer(error instanceof Error ? error.message : 'Unknown MCP request error.');
      setMcpTool('unavailable');
      setStatus('error');
    }
  };

  useEffect(() => {
    const preset = MCP_PRESETS[0];
    runQuery(preset.query, preset.zone, preset.toolName, preset.toolArguments);
  }, []);

  const handleSelectPreset = (preset: McpPreset) => {
    setSelectedPreset(preset);
    runQuery(preset.query, preset.zone, preset.toolName, preset.toolArguments);
  };

  const handleCustomQuery = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customInput.trim();
    if (!trimmed) return;
    const lowered = trimmed.toLowerCase();
    const codeLike = /(\n|;|=>|\b(def|function|class|return|const|let|var|for|while|import)\b)/.test(trimmed);
    const regions = [
      { zone: 'IE', aliases: ['ireland', 'eu-west-1'] },
      { zone: 'US-MIDA-PJM', aliases: ['virginia', 'mid-atlantic', 'us-east-1'] },
      { zone: 'US-CAL-CISO', aliases: ['california', 'us-west-1'] },
      { zone: 'SE', aliases: ['sweden'] },
      { zone: 'DE', aliases: ['germany', 'eu-central-1'] },
    ].filter((region) => region.aliases.some((alias) => lowered.includes(alias)));
    const matchedZones = [...new Set(regions.map((region) => region.zone))];
    if (lowered.includes('refactor') && codeLike) {
      runQuery(trimmed, activeZone, 'refactor_code', {
        source_code: trimmed,
        language: /(\bfunction\b|\b(const|let|var)\b|=>)/.test(trimmed) ? 'javascript' : 'python',
        guidance: 'Preserve behavior and explain any unverified optimization.',
      });
    } else if (lowered.includes('audit') && codeLike) {
      runQuery(trimmed, activeZone, 'audit_and_score', {
        source_code: trimmed,
        language: /(\bfunction\b|\b(const|let|var)\b|=>)/.test(trimmed) ? 'javascript' : 'python',
        zone: activeZone,
      });
    } else if (lowered.includes('compare') || (matchedZones.length > 1 && lowered.includes('region'))) {
      const zones = matchedZones.length > 1 ? matchedZones : ['IE', 'US-MIDA-PJM'];
      runQuery(trimmed, activeZone, 'compare_regions', { zones });
    } else if (lowered.includes('sci') || lowered.includes('software carbon intensity')) {
      runQuery(trimmed, activeZone, 'calculate_sci', {
        energy_joules: 45,
        duration_seconds: 1.5,
        functional_unit: 1,
        zone: matchedZones[0] ?? activeZone,
      });
    } else if (lowered.includes('intensity') || lowered.includes('grid') || lowered.includes('carbon')) {
      runQuery(trimmed, matchedZones[0] ?? activeZone, 'get_grid_intensity', {
        zone: matchedZones[0] ?? activeZone,
      });
    } else {
      setExpanded(true);
      setActiveQuery(trimmed);
      setAnswer('Choose a preset, or enter code with “audit” or “refactor”. Grid questions use the selected zone.');
      setMcpTool('no matching MCP tool');
      setStatus('error');
    }
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
              <span className={`w-1.5 h-1.5 rounded-full ${status === 'error' ? 'bg-rose-400' : status === 'ready' ? 'bg-emerald-400' : 'bg-amber-400'}`} />
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
                      {answer ?? t('alexa.error')}
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
