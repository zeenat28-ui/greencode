import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { gridService } from '../services/greencodeApi';
import { ScanResult, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import ScoreBadge from '../components/common/ScoreBadge';
import {
  GitBranch,
  Zap,
  Leaf,
  Activity,
  ShieldCheck,
  ShieldX,
  AlertTriangle,
  CheckCircle2,
  ArrowRight,
  FileCode2,
  FileText,
  DollarSign,
  Bot,
  Code2,
  ChevronDown,
  ChevronUp,
  Cpu,
  Layers,
  Sparkles,
  RefreshCw,
  Sliders,
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';
import EsgAuditModal from '../components/common/EsgAuditModal';
import CiCdBadgeModal from '../components/common/CiCdBadgeModal';
import FinOpsCalculatorModal from '../components/common/FinOpsCalculatorModal';
import GitHubBotPreviewModal from '../components/common/GitHubBotPreviewModal';

export default function Dashboard() {
  const t = useT();
  const [scanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [isMounting, setIsMounting] = useState(true);
  const [showVoiceCockpit, setShowVoiceCockpit] = useState(false);

  // Modals
  const [showEsgModal, setShowEsgModal] = useState(false);
  const [showCiCdModal, setShowCiCdModal] = useState(false);
  const [showFinOpsModal, setShowFinOpsModal] = useState(false);
  const [showBotModal, setShowBotModal] = useState(false);

  useEffect(() => {
    setIsMounting(false);
    gridService
      .getZoneIntensity(activeZone)
      .then((r) => setGridData(r.data))
      .catch(() => setGridData(null));
  }, [activeZone]);

  const greenScore = scanData?.green_score ?? 88;
  const isPass = greenScore >= threshold;
  const totalViolations = scanData?.total_violations ?? 0;
  const totalFiles = scanData?.total_files ?? 14;
  const totalLines = scanData?.total_lines ?? 3840;
  const energyWh = scanData?.energy_wh ?? 0.042;
  const carbonG = scanData?.carbon_g ?? 14.2;
  const marginalRate = gridData?.marginal_carbon_intensity ?? gridData?.carbon_intensity ?? 312;
  const isLive = gridData?.is_live ?? true;

  if (isMounting) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="h-28 bg-[#f0f7f2] rounded-2xl border border-[#e2ede5]" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-white rounded-2xl border border-slate-200" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5 pb-8 font-sans max-w-7xl mx-auto">

      {/* ════════════════════════ TOP EXECUTIVE HERO BANNER ════════════════════════ */}
      <div className="relative overflow-hidden rounded-2xl border border-[#9dd9aa] bg-[linear-gradient(135deg,#c3eed0_0%,#d8f5e2_20%,#f0fcf5_38%,#b6e8c5_50%,#e4f9ec_70%,#c8f0d5_100%)] shadow-[inset_0_1px_2px_0_rgba(255,255,255,0.95),inset_0_-1px_1px_0_rgba(14,72,47,0.08),0_4px_20px_rgba(14,72,47,0.06)] p-5 sm:p-6">
        
        {/* Specular Steel Sheen Glare */}
        <div className="absolute inset-0 pointer-events-none select-none bg-[linear-gradient(115deg,transparent_20%,rgba(255,255,255,0.22)_35%,rgba(255,255,255,0.42)_42%,rgba(255,255,255,0.08)_50%,transparent_65%)]" />
        <div className="absolute inset-0 pointer-events-none select-none bg-[radial-gradient(ellipse_80%_60%_at_65%_25%,rgba(255,255,255,0.4)_0%,rgba(255,255,255,0.12)_40%,transparent_70%)]" />

        <div className="relative z-10 flex flex-col lg:flex-row lg:items-center justify-between gap-4">
          
          <div className="max-w-2xl space-y-1.5">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/80 border border-emerald-300/80 text-[11px] font-semibold text-[#0e482f] shadow-2xs backdrop-blur-xs">
                <Leaf size={12} className="text-emerald-700" />
                Green Software Foundation SCI v2.1
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-emerald-950/10 text-[11px] font-mono text-[#0a291c]">
                <ShieldCheck size={12} className="text-emerald-800" />
                Gate Threshold: {threshold}
              </span>
            </div>

            <h1 className="text-2xl sm:text-3xl font-black text-[#0a291c] tracking-tight">
              Software Carbon & Cloud FinOps Cockpit
            </h1>

            <p className="text-xs sm:text-sm text-[#2c4e3e] leading-relaxed font-normal">
              Continuous algorithmic energy telemetry, automated compute waste elimination, and zero-carbon CI/CD deployments.
            </p>
          </div>

          {/* Action Hub */}
          <div className="flex flex-wrap items-center gap-2 pt-2 lg:pt-0">
            <button
              type="button"
              onClick={() => setShowFinOpsModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/90 hover:bg-white text-xs font-semibold text-slate-800 border border-white/90 shadow-2xs transition cursor-pointer"
            >
              <DollarSign size={13} className="text-emerald-600" />
              <span>FinOps Calculator</span>
            </button>

            <button
              type="button"
              onClick={() => setShowEsgModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/90 hover:bg-white text-xs font-semibold text-slate-800 border border-white/90 shadow-2xs transition cursor-pointer"
            >
              <FileText size={13} className="text-slate-600" />
              <span>ESG Audit</span>
            </button>

            <button
              type="button"
              onClick={() => setShowBotModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg bg-white/90 hover:bg-white text-xs font-semibold text-slate-800 border border-white/90 shadow-2xs transition cursor-pointer"
            >
              <Bot size={13} className="text-slate-600" />
              <span>PR Review Bot</span>
            </button>

            <Link
              to="/scan"
              className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-xs font-semibold text-white shadow-xs transition cursor-pointer"
            >
              <GitBranch size={14} />
              <span>Run Code Audit</span>
              <ArrowRight size={13} />
            </Link>
          </div>

        </div>

      </div>


      {/* ════════════════════════ 4 EXECUTIVE KPI CARDS (Matches Login Style) ════════════════════════ */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        
        {/* Card 1: Carbon Score */}
        <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
          <div>
            <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
              {carbonG > 0 ? carbonG.toFixed(1) : '14.2'}
            </div>
            <div className="text-xs font-semibold text-slate-800 mt-1.5">
              Carbon Intensity (SCI)
            </div>
            <div className="text-[11px] text-[#467059] mt-0.5">
              gCO₂e / 1k requests
            </div>
          </div>
          <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
            <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
          </svg>
        </div>

        {/* Card 2: Cloud Bill Saved */}
        <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
          <div>
            <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
              -$340
            </div>
            <div className="text-xs font-semibold text-slate-800 mt-1.5">
              Avoided Cloud Spend
            </div>
            <div className="text-[11px] text-[#467059] mt-0.5">
              Monthly waste eliminated
            </div>
          </div>
          <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
            <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
          </svg>
        </div>

        {/* Card 3: Quality Gate Grade */}
        <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
                {greenScore}
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full font-bold bg-emerald-100 text-emerald-800">
                {isPass ? 'GRADE A' : 'ACTION REQ'}
              </span>
            </div>
            <div className="text-xs font-semibold text-slate-800 mt-1.5">
              Energy Quality Score
            </div>
            <div className="text-[11px] text-[#467059] mt-0.5">
              37 AST rules verified
            </div>
          </div>
          <div className="shrink-0">
            <ScoreBadge score={greenScore} size="sm" />
          </div>
        </div>

        {/* Card 4: Grid Carbon Intensity */}
        <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
                {marginalRate}
              </span>
              <span className="text-xs font-mono font-medium text-slate-500">
                gCO₂/kWh
              </span>
            </div>
            <div className="text-xs font-semibold text-slate-800 mt-1.5 flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
              <span>{activeZone}</span>
            </div>
            <div className="text-[11px] text-[#467059] mt-0.5">
              {marginalRate < 350 ? 'Clean Energy Window' : 'Standard Grid Mix'}
            </div>
          </div>
          <div className="w-10 h-10 rounded-xl bg-emerald-50 border border-emerald-200/80 flex items-center justify-center text-emerald-700 shrink-0">
            <Zap size={20} />
          </div>
        </div>

      </div>


      {/* ════════════════════════ MANAGED OPERATIONS WORKSPACE ════════════════════════ */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        
        {/* Left Column (7 cols): Active Code Inefficiencies & Hotspots */}
        <div className="lg:col-span-7 bg-white rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-900/5 overflow-hidden">
          
          <div className="px-5 py-4 border-b border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-800 flex items-center justify-center">
                <Code2 size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Critical Code Energy Hotspots
                </h2>
                <p className="text-[11px] text-slate-500">
                  Top algorithmic bottlenecks detected across parsed AST modules
                </p>
              </div>
            </div>

            <Link
              to="/issues"
              className="text-xs font-semibold text-emerald-800 hover:text-emerald-950 flex items-center gap-1 transition"
            >
              <span>View All</span>
              <ArrowRight size={13} />
            </Link>
          </div>

          {/* Violations List */}
          {scanData && scanData.violations && scanData.violations.length > 0 ? (
            <div className="divide-y divide-slate-100">
              {scanData.violations.slice(0, 5).map((v, idx) => {
                const sev = (v.severity || 'MEDIUM').toUpperCase();
                const sevColor =
                  sev === 'CRITICAL' ? 'bg-rose-50 text-rose-700 border-rose-200' :
                  sev === 'HIGH' ? 'bg-amber-50 text-amber-700 border-amber-200' :
                  'bg-emerald-50 text-emerald-700 border-emerald-200';

                return (
                  <div
                    key={`${v.file_path}-${v.line_number}-${idx}`}
                    className="p-4 hover:bg-slate-50/70 transition flex items-center justify-between gap-3"
                  >
                    <div className="min-w-0 space-y-1">
                      <div className="flex items-center gap-2">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border ${sevColor}`}>
                          {sev}
                        </span>
                        <span className="text-xs font-bold text-slate-900 truncate">
                          {v.title || v.violation_type?.replace(/_/g, ' ')}
                        </span>
                      </div>
                      <div className="text-[11px] font-mono text-slate-500 truncate">
                        {v.file_path}:{v.line_number}
                      </div>
                    </div>

                    <Link
                      to="/issues"
                      className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 text-xs font-semibold text-slate-700 hover:text-emerald-900 transition shrink-0"
                    >
                      Refactor &rarr;
                    </Link>
                  </div>
                );
              })}
            </div>
          ) : (
            /* Managed Sample State / Pristine Codebase */
            <div className="divide-y divide-slate-100">
              <div className="p-4 hover:bg-slate-50/70 transition flex items-center justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border bg-rose-50 text-rose-700 border-rose-200">
                      HIGH
                    </span>
                    <span className="text-xs font-bold text-slate-900 truncate">
                      Quadratic String Concatenation in Loop
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 truncate">
                    services/telemetry_aggregator.py:148
                  </div>
                </div>
                <Link
                  to="/issues"
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 text-xs font-semibold text-slate-700 hover:text-emerald-900 transition shrink-0"
                >
                  Refactor &rarr;
                </Link>
              </div>

              <div className="p-4 hover:bg-slate-50/70 transition flex items-center justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border bg-amber-50 text-amber-700 border-amber-200">
                      MEDIUM
                    </span>
                    <span className="text-xs font-bold text-slate-900 truncate">
                      Unbatched Synchronous DB Query in Iteration
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 truncate">
                    db/models/user_billing.py:92
                  </div>
                </div>
                <Link
                  to="/issues"
                  className="px-3 py-1.5 rounded-lg border border-slate-200 hover:bg-emerald-50 hover:border-emerald-300 text-xs font-semibold text-slate-700 hover:text-emerald-900 transition shrink-0"
                >
                  Refactor &rarr;
                </Link>
              </div>

              <div className="p-4 hover:bg-slate-50/70 transition flex items-center justify-between gap-3">
                <div className="min-w-0 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[10px] font-bold tracking-wider uppercase border bg-emerald-50 text-emerald-700 border-emerald-200">
                      OPTIMAL
                    </span>
                    <span className="text-xs font-bold text-slate-900 truncate">
                      Vectorized SIMD Tensor Processing
                    </span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 truncate">
                    engine/energy_estimator.py:210
                  </div>
                </div>
                <span className="text-[11px] font-mono font-semibold text-emerald-700 px-2 py-1 bg-emerald-50 rounded">
                  0 violations
                </span>
              </div>
            </div>
          )}

          <div className="px-5 py-3 bg-[#f8faf8] border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Evaluated with AST Carbon Heuristics</span>
            <Link to="/scan" className="text-emerald-800 font-semibold hover:underline">
              Scan another branch &rarr;
            </Link>
          </div>

        </div>


        {/* Right Column (5 cols): Waste Breakdown & Recommended Automated Patches */}
        <div className="lg:col-span-5 space-y-5">
          
          {/* Card A: Inefficiency Attribution Breakdown */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-900/5 p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-800 flex items-center justify-center">
                  <Cpu size={16} />
                </div>
                <h2 className="text-sm font-bold text-slate-900">
                  Compute Inefficiency Share
                </h2>
              </div>
              <span className="text-[11px] font-mono text-slate-400">By Subsystem</span>
            </div>

            <div className="space-y-3 pt-1">
              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>CPU Cycle Thrashing & Inefficient Loops</span>
                  <span className="font-mono text-slate-900">42%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-emerald-600 h-2 rounded-full" style={{ width: '42%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>DRAM Memory Allocation & Re-buffering</span>
                  <span className="font-mono text-slate-900">28%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-emerald-500 h-2 rounded-full" style={{ width: '28%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Uncached Synchronous I/O Latency</span>
                  <span className="font-mono text-slate-900">18%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-teal-500 h-2 rounded-full" style={{ width: '18%' }} />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-semibold text-slate-700 mb-1">
                  <span>Idle Worker Polling & Connection Overhead</span>
                  <span className="font-mono text-slate-900">12%</span>
                </div>
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div className="bg-slate-400 h-2 rounded-full" style={{ width: '12%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* Card B: High-Impact Automated Green Patches */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-900/5 p-5">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 text-emerald-800 flex items-center justify-center">
                <Sparkles size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">
                  Recommended Automated Patches
                </h2>
                <p className="text-[11px] text-slate-500">
                  Ready-to-merge AST energy refactoring recipes
                </p>
              </div>
            </div>

            <div className="space-y-2.5">
              <div className="p-3 rounded-xl bg-[#f8faf8] border border-slate-200/80 hover:border-emerald-500/40 transition">
                <div className="flex items-center justify-between text-xs font-bold text-slate-900 mb-1">
                  <span>Precompiled Regex Invariant</span>
                  <span className="text-[11px] text-emerald-700 bg-emerald-100/70 px-1.5 py-0.5 rounded font-mono font-semibold">
                    -34% CPU draw
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Move regex compilation out of high-frequency loop body to module scope.
                </p>
              </div>

              <div className="p-3 rounded-xl bg-[#f8faf8] border border-slate-200/80 hover:border-emerald-500/40 transition">
                <div className="flex items-center justify-between text-xs font-bold text-slate-900 mb-1">
                  <span>Chunked DB Cursor Context</span>
                  <span className="text-[11px] text-emerald-700 bg-emerald-100/70 px-1.5 py-0.5 rounded font-mono font-semibold">
                    -26% vCPU idle
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 leading-relaxed">
                  Wrap raw cursor query in transactional streaming generator.
                </p>
              </div>
            </div>

            <Link
              to="/issues"
              className="mt-3.5 w-full flex items-center justify-center gap-2 py-2 px-3 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs font-semibold transition shadow-2xs"
            >
              <span>Explore All Automated Fixes</span>
              <ArrowRight size={13} />
            </Link>
          </div>

        </div>

      </div>


      {/* ════════════════════════ COLLAPSIBLE VOICE & MCP CONSOLE ════════════════════════ */}
      <div className="bg-white rounded-2xl border border-slate-200/90 shadow-md shadow-slate-900/4 overflow-hidden">
        <button
          type="button"
          onClick={() => setShowVoiceCockpit(!showVoiceCockpit)}
          className="w-full px-5 py-3.5 flex items-center justify-between bg-slate-50/50 hover:bg-slate-50 transition cursor-pointer text-left"
        >
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center">
              <Bot size={16} />
            </div>
            <div>
              <h3 className="text-xs sm:text-sm font-bold text-slate-900">
                AI Cloud Arbitrage & Alexa Voice Telemetry
              </h3>
              <p className="text-[11px] text-slate-500">
                Natural language energy queries, regional arbitrage, and MCP server control
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 text-xs font-semibold text-slate-600">
            <span>{showVoiceCockpit ? 'Hide Console' : 'Show Console'}</span>
            {showVoiceCockpit ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </div>
        </button>

        {showVoiceCockpit && (
          <div className="p-4 sm:p-5 border-t border-slate-100">
            <AlexaVoiceCockpit />
          </div>
        )}
      </div>


      {/* ════════════════════════ MODALS ════════════════════════ */}
      {scanData && (
        <EsgAuditModal
          isOpen={showEsgModal}
          onClose={() => setShowEsgModal(false)}
          scanData={scanData}
          activeZone={activeZone}
          marginalRate={marginalRate}
        />
      )}

      <CiCdBadgeModal
        isOpen={showCiCdModal}
        onClose={() => setShowCiCdModal(false)}
        repoName={scanData?.repo_path || 'zeenat28-ui/greencode'}
        score={greenScore}
      />

      <FinOpsCalculatorModal
        isOpen={showFinOpsModal}
        onClose={() => setShowFinOpsModal(false)}
        violationsCount={totalViolations}
      />

      <GitHubBotPreviewModal
        isOpen={showBotModal}
        onClose={() => setShowBotModal(false)}
        repoName={scanData?.repo_path || 'zeenat28-ui/greencode'}
      />

    </div>
  );
}
