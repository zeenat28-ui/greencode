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
  RefreshCw,
  FileCode2,
  FileText,
  DollarSign,
  Bot,
  Calculator,
  Code2,
} from 'lucide-react';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';
import EsgAuditModal from '../components/common/EsgAuditModal';
import CiCdBadgeModal from '../components/common/CiCdBadgeModal';
import FinOpsCalculatorModal from '../components/common/FinOpsCalculatorModal';
import GitHubBotPreviewModal from '../components/common/GitHubBotPreviewModal';
import { DEMO_SCAN_DATA } from '../utils/demoData';

export default function Dashboard() {
  const [scanData, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [isMounting, setIsMounting] = useState(true);
  const [loadingSample, setLoadingSample] = useState(false);
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

  const handleScanSample = async () => {
    setLoadingSample(true);
    try {
      const res = await fetch('/api/scan/local-workspace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subpath: 'samples',
          repo_name: 'greencode-org/samples-benchmark',
          team_id: 'core-platform',
        }),
      });
      if (res.ok) {
        const liveData = await res.json();
        setScanData(liveData);
        return;
      }
      const history = await scanService.getHistory(1, 0);
      const latest = history.data.repositories?.[0];
      if (latest?.full_name) {
        const resp = await scanService.scanGitHub(latest.full_name, latest.default_branch || undefined);
        setScanData(resp.data);
      } else {
        setScanData(Object.values(DEMO_SCAN_DATA)[0]);
      }
    } catch {
      setScanData(Object.values(DEMO_SCAN_DATA)[0]);
    } finally {
      setLoadingSample(false);
    }
  };

  const greenScore = scanData?.green_score ?? 0;
  const isPass = greenScore >= threshold;
  const totalViolations = scanData?.total_violations ?? 0;
  const totalFiles = scanData?.total_files ?? 0;
  const totalLines = scanData?.total_lines ?? 0;
  const energyWh = scanData?.energy_wh ?? 0;
  const carbonG = scanData?.carbon_g ?? 0;
  const marginalRate = gridData?.marginal_carbon_intensity ?? gridData?.carbon_intensity ?? null;
  const isLive = gridData?.is_live ?? false;
  const annualSavingsUsd = Math.round(((totalViolations * 1.8 * 8760) / 1000) * 0.14 + totalViolations * 180);

  if (isMounting) {
    return (
      <div className="space-y-5 animate-pulse">
        <div className="h-8 w-56 bg-zinc-200 rounded-lg" />
        <div className="h-28 bg-zinc-100 rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-zinc-100 rounded-xl" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      {/* Row 1: Unified Enterprise Workspace Header */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-1 border-b border-zinc-200/80">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-lg font-semibold text-zinc-950 tracking-tight">
              Repository Telemetry
            </h1>
            {scanData && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-zinc-100 border border-zinc-200/80 text-xs font-mono text-zinc-700 truncate max-w-xs">
                <GitBranch size={12} className="text-zinc-500 shrink-0" />
                <span className="truncate">{scanData.repo_path}</span>
              </span>
            )}
            <span className="hidden sm:inline-block text-[11px] font-mono text-zinc-400">
              ISO/IEC 21031:2024 (GSF SCI)
            </span>
          </div>
        </div>

        {/* Clean Single-Row Action Bar */}
        <div className="flex flex-wrap items-center gap-1.5">
          {scanData && (
            <>
              <button
                onClick={() => setShowFinOpsModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
                title="FinOps FOCUS 1.4 Cloud Cost Attribution"
              >
                <DollarSign size={13} className="text-emerald-600" />
                <span>FinOps ROI</span>
              </button>
              <button
                onClick={() => setShowBotModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
                title="Preview Automated PR Diff Comment"
              >
                <Bot size={13} className="text-zinc-600" />
                <span>PR Bot</span>
              </button>
              <button
                onClick={() => setShowEsgModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
                title="Export GSF SCI Audit Certificate"
              >
                <FileText size={13} className="text-zinc-600" />
                <span>ESG Report</span>
              </button>
              <button
                onClick={() => setShowCiCdModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
                title="GitHub Actions & SARIF 2.1.0 Gate"
              >
                <ShieldCheck size={13} className="text-zinc-600" />
                <span>CI/CD Gate</span>
              </button>
              <button
                onClick={handleScanSample}
                disabled={loadingSample}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
                title="Execute Reference Benchmark Suite"
              >
                <RefreshCw size={13} className={loadingSample ? 'animate-spin text-emerald-600' : 'text-zinc-500'} />
                <span>{loadingSample ? 'Running...' : 'Benchmark'}</span>
              </button>
            </>
          )}
          <Link
            to="/scan"
            className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5 whitespace-nowrap"
          >
            <GitBranch size={13} />
            <span>Scan Repository</span>
          </Link>
        </div>
      </div>

      {/* Row 2: Above-the-Fold Quality Gate Hero + 4 Core Engineering KPIs */}
      {scanData ? (
        <>
          <div className="card p-5 flex flex-col md:flex-row md:items-center justify-between gap-5">
            <div className="flex items-center gap-5 min-w-0">
              <div className="shrink-0">
                <ScoreBadge score={greenScore} size="md" />
              </div>

              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span
                    className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${
                      isPass
                        ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                        : 'bg-rose-50 text-rose-800 border border-rose-200'
                    }`}
                  >
                    {isPass ? <ShieldCheck size={12} /> : <ShieldX size={12} />}
                    {isPass ? 'Quality Gate Passed' : 'Gate Failed'}
                  </span>
                  <span className="text-xs text-zinc-400 font-mono">
                    Threshold &ge; {threshold}/100
                  </span>
                </div>

                <h2 className="text-sm font-semibold text-zinc-950 leading-snug">
                  {totalViolations === 0
                    ? 'Zero algorithmic or I/O energy bottlenecks detected across scanned modules.'
                    : `${totalViolations} efficiency bottleneck${totalViolations !== 1 ? 's' : ''} detected across ${totalFiles} analyzed files (${totalLines.toLocaleString()} LOC).`}
                </h2>

                <div className="flex flex-wrap items-center gap-2.5 mt-1.5 text-xs text-zinc-500 font-mono">
                  <span>{totalFiles} files</span>
                  <span>&middot;</span>
                  <span>{totalLines.toLocaleString()} lines</span>
                  {marginalRate !== null && (
                    <>
                      <span>&middot;</span>
                      <span className="inline-flex items-center gap-1.5 text-zinc-700">
                        <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
                        <span>{activeZone}: {marginalRate} gCO₂/kWh</span>
                      </span>
                    </>
                  )}
                </div>
              </div>
            </div>

            <div className="shrink-0 flex items-center gap-2">
              {totalViolations > 0 ? (
                <Link
                  to="/issues"
                  className="btn-primary flex items-center gap-1.5 text-xs px-3.5 py-2 whitespace-nowrap"
                >
                  <AlertTriangle size={13} className="text-amber-400" />
                  <span>Inspect &amp; Patch {totalViolations} Findings</span>
                  <ArrowRight size={13} />
                </Link>
              ) : (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-900 text-xs font-medium border border-emerald-200 font-mono">
                  <CheckCircle2 size={14} className="text-emerald-600" />
                  <span>100% Optimal</span>
                </div>
              )}
            </div>
          </div>

          {/* 4 High-Precision Engineering Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title="Static & Call-Graph Issues"
              value={totalViolations}
              subtitle={totalViolations === 0 ? 'Zero bottlenecks detected' : `${totalViolations} hotspots flagged in AST`}
              icon={<Activity size={15} />}
              accentColor={totalViolations > 0 ? '#E11D48' : '#059669'}
            />
            <MetricCard
              title="Runtime Energy Draw"
              value={energyWh > 0 ? `${(energyWh * 1000).toFixed(2)} mWh` : '0.00 mWh'}
              subtitle="RAPL / cgroup v2 attribution"
              icon={<Zap size={15} />}
            />
            <MetricCard
              title="SCI Carbon Intensity"
              value={carbonG > 0 ? `${carbonG.toFixed(4)} g` : '0.0000 g'}
              subtitle={marginalRate !== null ? `${marginalRate} gCO₂/kWh (${activeZone})` : 'Regional marginal grid'}
              icon={<Leaf size={15} />}
            />
            <MetricCard
              title="Cloud FinOps Delta"
              value={totalViolations > 0 ? `-$${annualSavingsUsd.toLocaleString()}/yr` : '$0/yr'}
              subtitle="FOCUS 1.4 projected EC2 savings"
              icon={<Calculator size={15} />}
              accentColor={totalViolations > 0 ? '#059669' : undefined}
            />
          </div>

          {/* Row 3: Two-Column Engineering Workspace (Findings Table + Rule Breakdown) */}
          <div className="grid lg:grid-cols-12 gap-5 items-start">
            {/* Left 7 Cols: Active Code Efficiency Findings Table */}
            <div className="lg:col-span-7 card overflow-hidden">
              <div className="px-5 py-3.5 border-b border-zinc-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 size={15} className="text-zinc-500" />
                  <h3 className="section-title">Detected Code Hotspots</h3>
                  <span className="text-[11px] font-mono px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600">
                    {scanData.violations?.length || 0}
                  </span>
                </div>
                <Link
                  to="/issues"
                  className="text-xs font-medium text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
                >
                  <span>Open Diff Remediator</span>
                  <ArrowRight size={12} />
                </Link>
              </div>

              {scanData.violations && scanData.violations.length > 0 ? (
                <div className="divide-y divide-zinc-100">
                  {scanData.violations.slice(0, 5).map((v, idx) => {
                    const sev = (v.severity || 'MEDIUM').toUpperCase();
                    const sevBadge =
                      sev === 'CRITICAL'
                        ? 'bg-rose-50 text-rose-700 border-rose-200'
                        : sev === 'HIGH'
                        ? 'bg-amber-50 text-amber-800 border-amber-200'
                        : 'bg-zinc-100 text-zinc-700 border-zinc-200';
                    return (
                      <div
                        key={`${v.file_path}-${v.line_number}-${idx}`}
                        className="px-5 py-3 hover:bg-zinc-50/80 transition-colors flex items-start justify-between gap-3"
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <span
                              className={`text-[10px] font-mono font-semibold px-1.5 py-0.5 rounded border ${sevBadge}`}
                            >
                              {sev}
                            </span>
                            <span className="text-xs font-semibold text-zinc-900 truncate">
                              {v.title || v.violation_type}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-zinc-500 truncate">
                            {v.file_path}:{v.line_number}
                          </div>
                        </div>
                        <Link
                          to="/issues"
                          className="shrink-0 text-[11px] font-mono font-medium text-zinc-600 hover:text-zinc-950 px-2.5 py-1 rounded border border-zinc-200 hover:border-zinc-300 bg-white transition-colors"
                        >
                          Patch &rarr;
                        </Link>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-zinc-500">
                  No efficiency violations detected in this repository scan.
                </div>
              )}
            </div>

            {/* Right 5 Cols: Algorithmic Breakdown & Language Distribution */}
            <div className="lg:col-span-5 space-y-5">
              <div className="card p-5">
                <div className="mb-3">
                  <h3 className="section-title">Algorithmic Rule Breakdown</h3>
                  <p className="text-[11px] text-zinc-500 mt-0.5">
                    Grouped by AST &amp; call-graph violation pattern
                  </p>
                </div>
                <ViolationChart breakdown={scanData.violation_breakdown} />
              </div>

              {scanData.file_results && scanData.file_results.length > 0 && (
                <div className="card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="section-title">Language Telemetry</h3>
                    <span className="text-[11px] font-mono text-zinc-500">
                      <FileCode2 size={12} className="inline mr-1" />
                      {scanData.file_results.length} files
                    </span>
                  </div>
                  <LanguageBreakdown fileResults={scanData.file_results} />
                </div>
              )}
            </div>
          </div>
        </>
      ) : (
        /* Empty State */
        <div className="card p-10 text-center">
          <div className="w-11 h-11 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto mb-3 text-zinc-700">
            <GitBranch size={20} />
          </div>
          <h2 className="text-sm font-semibold text-zinc-900 mb-1">No Active Repository Telemetry</h2>
          <p className="text-xs text-zinc-500 max-w-md mx-auto mb-5 leading-relaxed">
            Audit a local directory, upload a source archive, or connect a GitHub repository to compute GSF SCI metrics and synthesize AST remediations.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5">
            <button
              onClick={handleScanSample}
              disabled={loadingSample}
              className="btn-secondary flex items-center gap-2 text-xs px-4 py-2"
            >
              <RefreshCw size={13} className={loadingSample ? 'animate-spin text-emerald-600' : 'text-zinc-600'} />
              <span>{loadingSample ? 'Analyzing Reference Suite...' : 'Run Reference Benchmark Suite'}</span>
            </button>
            <Link to="/scan" className="btn-primary flex items-center gap-2 text-xs px-4 py-2">
              <GitBranch size={13} />
              <span>Scan Repository</span>
            </Link>
          </div>
        </div>
      )}

      {/* Row 4: Compact MCP 2025-11-25 & Voice Command Console */}
      <AlexaVoiceCockpit />

      {/* Modals */}
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
        repoName={scanData?.repo_path || 'greencode-org/greencode'}
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

function LanguageBreakdown({ fileResults }: { fileResults: any[] }) {
  const langCount: Record<string, number> = {};
  fileResults.forEach((f) => {
    const lang = f.language || 'unknown';
    langCount[lang] = (langCount[lang] || 0) + 1;
  });

  const sorted = Object.entries(langCount).sort((a, b) => b[1] - a[1]);
  const max = sorted[0]?.[1] ?? 1;

  return (
    <div className="space-y-3 pt-1">
      {sorted.map(([lang, count]) => (
        <div key={lang} className="space-y-1">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-zinc-700 uppercase tracking-wide">{lang}</span>
            <span className="font-mono text-zinc-500">
              {count} {count === 1 ? 'file' : 'files'}
            </span>
          </div>
          <div className="w-full bg-zinc-100 rounded-full h-1.5 overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500 bg-emerald-600"
              style={{ width: `${(count / max) * 100}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
