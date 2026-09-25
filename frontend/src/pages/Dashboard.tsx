import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { scanService, gridService } from '../services/greencodeApi';
import { ScanResult, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import ScoreBadge from '../components/common/ScoreBadge';
import MetricCard from '../components/common/MetricCard';
import ViolationChart from '../components/charts/ViolationChart';
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
  Play,
  RefreshCw,
  Sparkles,
  FileCode2,
  Cpu
} from 'lucide-react';
import { theme } from '../styles/theme';

export default function Dashboard() {
  const [scanData, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [isMounting, setIsMounting] = useState(true);
  const [loadingSample, setLoadingSample] = useState(false);

  useEffect(() => {
    setIsMounting(false);
    gridService
      .getZoneIntensity(activeZone)
      .then((r) => setGridData(r.data))
      .catch(() => setGridData(null));
  }, [activeZone]);

  const handleScanSample = async () => {
    setLoadingSample(true);
    try {
      // Re-run the most recent audit, if there is one, to refresh the dashboard.
      const history = await scanService.getHistory(1, 0);
      const latest = history.data.repositories?.[0];
      if (!latest?.full_name) return;
      const resp = await scanService.scanGitHub(latest.full_name, latest.default_branch || undefined);
      setScanData(resp.data);
    } catch {
      // Keep the previously loaded scan visible on failure.
    } finally {
      setLoadingSample(false);
    }
  };

  const greenScore      = scanData?.green_score ?? 0;
  const isPass          = greenScore >= threshold;
  const totalViolations = scanData?.total_violations ?? 0;
  const totalFiles      = scanData?.total_files ?? 0;
  const totalLines      = scanData?.total_lines ?? 0;
  const energyWh        = scanData?.energy_wh ?? 0;
  const carbonG         = scanData?.carbon_g ?? 0;
  const marginalRate    = gridData?.marginal_carbon_intensity ?? gridData?.carbon_intensity ?? null;
  const cleanPct        = gridData?.clean_energy_percentage ?? null;
  const isLive          = gridData?.is_live ?? false;

  // Prevent flicker during initial state reconciliation
  if (isMounting) {
    return (
      <div className="space-y-6 animate-pulse">
        <div className="h-8 w-48 bg-slate-200 rounded-lg" />
        <div className="h-32 bg-slate-100 rounded-2xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-24 bg-slate-100 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Audit Dashboard</h1>
          <p className="text-sm text-slate-500 mt-0.5 flex items-center gap-1.5">
            {scanData ? (
              <>
                <span className="font-semibold text-slate-700 truncate max-w-md">{scanData.repo_path}</span>
                <span className="text-slate-300">·</span>
                <span>Audited for ISO/IEC 21031 &amp; GSF SCI</span>
              </>
            ) : (
              'Connect a repository or run a scan to start green auditing'
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {scanData && (
            <button
              onClick={handleScanSample}
              disabled={loadingSample}
              className="btn-secondary text-xs font-semibold px-3 py-2 flex items-center gap-1.5"
              title="Re-run benchmark against sample test suite"
            >
              <Sparkles size={13} className="text-emerald-600" />
              {loadingSample ? 'Auditing...' : 'Run Samples Demo'}
            </button>
          )}
          <Link to="/scan" className="btn-primary text-xs font-semibold px-3.5 py-2 flex items-center gap-1.5">
            <GitBranch size={13} />
            Scan Repository
          </Link>
        </div>
      </div>

      {/* Quality Gate hero */}
      {scanData ? (
        <div
          className={`card p-6 flex flex-col md:flex-row md:items-center gap-6 border-2 transition-all ${
            isPass
              ? 'border-emerald-200 bg-emerald-50/40 shadow-sm'
              : 'border-red-200 bg-red-50/30 shadow-sm'
          }`}
        >
          <div className="shrink-0 flex justify-center">
            <ScoreBadge score={greenScore} size="lg" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-extrabold uppercase tracking-wider px-2 py-0.5 rounded-full ${
                  isPass ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                }`}
              >
                {isPass ? <ShieldCheck size={14} /> : <ShieldX size={14} />}
                {isPass ? 'Quality Gate Passed' : 'Quality Gate Blocked'}
              </span>
              <span className="text-xs text-slate-500 font-medium">Target Threshold: ≥ {threshold}</span>
            </div>

            <h2 className="text-lg font-bold text-slate-900 leading-snug">
              {isPass
                ? 'Source code adheres to Green Software Foundation sustainability guidelines'
                : `${totalViolations} energy anti-pattern${totalViolations !== 1 ? 's' : ''} detected that exceed carbon budgets`}
            </h2>

            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-600">
              <span className="font-semibold text-slate-800">{totalFiles} audited files</span>
              <span className="text-slate-300">·</span>
              <span className="font-mono">{totalLines.toLocaleString()} LOC</span>
              {marginalRate !== null && (
                <>
                  <span className="text-slate-300">·</span>
                  <span className="inline-flex items-center gap-1.5 bg-white/80 px-2 py-0.5 rounded-md border border-slate-200/60">
                    <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                    <span className="font-semibold">{activeZone}</span>: {marginalRate} gCO₂/kWh
                  </span>
                </>
              )}
            </div>
          </div>

          {/* Action button on right */}
          <div className="shrink-0 flex items-center">
            {totalViolations > 0 ? (
              <Link
                to="/issues"
                className="btn-primary flex items-center gap-2 text-xs font-semibold px-4 py-2.5 shadow-sm"
              >
                <AlertTriangle size={14} />
                View {totalViolations} Issue{totalViolations !== 1 ? 's' : ''}
                <ArrowRight size={13} />
              </Link>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl bg-emerald-100 text-emerald-800 text-xs font-bold border border-emerald-200">
                <CheckCircle2 size={16} className="text-emerald-600" />
                Zero Violations Detected
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Empty State with 1-click sample demo */
        <div className="card p-10 sm:p-14 text-center">
          <div className="w-16 h-16 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4 text-emerald-600 shadow-sm">
            <GitBranch size={28} />
          </div>
          <h2 className="text-lg font-bold text-slate-900 mb-1.5">No repository scanned yet</h2>
          <p className="text-sm text-slate-500 max-w-md mx-auto mb-6 leading-relaxed">
            Audit a local codebase, upload a ZIP archive, or link a GitHub repository to evaluate algorithmic energy efficiency, carbon intensity, and synthesize GSF fixes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
            <button
              onClick={handleScanSample}
              disabled={loadingSample}
              className="btn-secondary flex items-center gap-2 text-xs font-semibold px-4 py-2.5 w-full sm:w-auto justify-center"
            >
              <Sparkles size={14} className="text-emerald-600" />
              {loadingSample ? 'Analyzing Sample Files...' : 'Run Demo on Sample Files'}
            </button>
            <Link
              to="/scan"
              className="btn-primary flex items-center gap-2 text-xs font-semibold px-5 py-2.5 w-full sm:w-auto justify-center"
            >
              <GitBranch size={14} />
              Scan a Repository
            </Link>
          </div>
        </div>
      )}

      {/* Metrics Grid */}
      {scanData && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Issues Detected"
            value={totalViolations}
            subtitle={`${totalFiles} files · ${totalLines.toLocaleString()} LOC`}
            icon={<Activity size={20} />}
            accentColor={totalViolations > 0 ? '#dc2626' : '#059669'}
          />
          <MetricCard
            title="Energy / Execution"
            value={energyWh > 0 ? `${(energyWh * 1000).toFixed(2)} mWh` : '—'}
            subtitle="Normalized baseline per run"
            icon={<Zap size={20} />}
            accentColor="#d97706"
          />
          <MetricCard
            title="Carbon Footprint"
            value={carbonG > 0 ? `${carbonG.toFixed(4)} g` : '—'}
            subtitle={
              marginalRate !== null
                ? `${marginalRate} g/kWh · ${cleanPct ?? '—'}% clean grid`
                : 'Awaiting regional grid telemetry'
            }
            icon={<Leaf size={20} />}
            accentColor="#059669"
          />
          <MetricCard
            title="Operational Energy"
            value={energyWh > 0 ? `${energyWh.toFixed(4)} Wh` : '—'}
            subtitle="Full execution cycle"
            icon={<Zap size={20} />}
          />
        </div>
      )}

      {/* Charts & Breakdown */}
      {scanData && scanData.violations?.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-5">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="section-title">Violations by Pattern</h3>
              <Link to="/issues" className="text-xs font-semibold text-emerald-700 hover:text-emerald-800 flex items-center gap-1">
                Synthesize Fixes <ArrowRight size={12} />
              </Link>
            </div>
            <ViolationChart breakdown={scanData.violation_breakdown} />
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="section-title">Language Composition</h3>
              <span className="text-xs text-slate-400 font-mono">
                {scanData.file_results?.length || 0} audited files
              </span>
            </div>
            {scanData.file_results?.length ? (
              <LanguageBreakdown fileResults={scanData.file_results} />
            ) : (
              <p className="text-sm text-slate-400 py-8 text-center">No language telemetry available</p>
            )}
          </div>
        </div>
      )}

      {/* Quick Navigation Footer Cards */}
      {scanData && (
        <div className="grid sm:grid-cols-3 gap-4 pt-2">
          <Link to="/issues" className="card p-5 hover:border-emerald-300 transition-all group">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-red-50 text-red-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <FileCode2 size={20} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-800">Review Anti-Patterns</p>
                <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                  Inspect code AST nodes and generate fixes
                </p>
              </div>
            </div>
          </Link>

          <Link to="/profiler" className="card p-5 hover:border-emerald-300 transition-all group">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Cpu size={20} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-800">Hardware Profiler</p>
                <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                  Benchmark CPU &amp; RAM in sandboxed runtime
                </p>
              </div>
            </div>
          </Link>

          <Link to="/history" className="card p-5 hover:border-emerald-300 transition-all group">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                <Leaf size={20} />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-bold text-slate-800">Audit History</p>
                <p className="text-[11px] text-slate-500 mt-0.5 truncate">
                  Track fleet green trends and cumulative savings
                </p>
              </div>
            </div>
          </Link>
        </div>
      )}
    </div>
  );
}

function LanguageBreakdown({ fileResults }: { fileResults: any[] }) {
  const langCount: Record<string, number> = {};
  fileResults.forEach(f => {
    const lang = f.language || 'unknown';
    langCount[lang] = (langCount[lang] || 0) + 1;
  });

  const sorted = Object.entries(langCount).sort((a, b) => b[1] - a[1]);
  const max    = sorted[0]?.[1] ?? 1;

  return (
    <div className="space-y-3.5 pt-2">
      {sorted.map(([lang, count]) => (
        <div key={lang} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-slate-700 uppercase tracking-wide">
              {lang}
            </span>
            <span className="font-mono text-slate-500">
              {count} {count === 1 ? 'file' : 'files'}
            </span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 bg-emerald-500"
              style={{
                width: `${(count / max) * 100}%`,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

