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
  Cpu,
  FileText,
  DollarSign,
  Bot,
  Calculator
} from 'lucide-react';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';
import EsgAuditModal from '../components/common/EsgAuditModal';
import CiCdBadgeModal from '../components/common/CiCdBadgeModal';
import FinOpsCalculatorModal from '../components/common/FinOpsCalculatorModal';
import GitHubBotPreviewModal from '../components/common/GitHubBotPreviewModal';
import { DEMO_SCAN_DATA } from '../utils/demoData';
import { theme } from '../styles/theme';

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
      // Re-run the most recent audit, if there is one, to refresh the dashboard.
      const history = await scanService.getHistory(1, 0);
      const latest = history.data.repositories?.[0];
      if (latest?.full_name) {
        const resp = await scanService.scanGitHub(latest.full_name, latest.default_branch || undefined);
        setScanData(resp.data);
      } else {
        // Instant sample evaluation for demonstration
        setScanData(Object.values(DEMO_SCAN_DATA)[0]);
      }
    } catch {
      // Load fallback demo benchmark on network issue
      setScanData(Object.values(DEMO_SCAN_DATA)[0]);
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
          <h1 className="text-xl font-bold text-slate-900 tracking-tight flex items-center gap-2">
            Code Sustainability Dashboard
          </h1>
          <p className="text-xs text-slate-500 mt-1 flex items-center gap-1.5">
            {scanData ? (
              <>
                <span className="font-semibold text-slate-700 font-mono truncate max-w-md">{scanData.repo_path}</span>
                <span className="text-slate-300">&middot;</span>
                <span>Scored under Green Software Foundation (GSF SCI) standards</span>
              </>
            ) : (
              'Scan a repository or run a demo benchmark to measure code efficiency.'
            )}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {scanData && (
            <>
              <button
                onClick={() => setShowFinOpsModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 border-emerald-300 text-emerald-950 bg-emerald-50/70 hover:bg-emerald-100 font-medium"
                title="Model AWS / GCP compute bill savings"
              >
                <DollarSign size={13} className="text-emerald-700" />
                FinOps ROI
              </button>
              <button
                onClick={() => setShowBotModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 border-blue-300 text-blue-950 bg-blue-50/70 hover:bg-blue-100 font-medium"
                title="Preview GreenCode GitHub PR Bot"
              >
                <Bot size={13} className="text-blue-600" />
                GitHub Bot
              </button>
              <button
                onClick={() => setShowEsgModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5 border-olive-300 text-olive-900 bg-olive-50/60 hover:bg-olive-100/70"
                title="View and print official GSF SCI compliance certificate"
              >
                <FileText size={13} className="text-olive-700" />
                ESG Report
              </button>
              <button
                onClick={() => setShowCiCdModal(true)}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
                title="Generate CI/CD gate workflow and README badges"
              >
                <ShieldCheck size={13} className="text-slate-600" />
                CI/CD
              </button>
              <button
                onClick={handleScanSample}
                disabled={loadingSample}
                className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
                title="Re-run benchmark against reference test suite"
              >
                <RefreshCw size={13} className={loadingSample ? 'animate-spin text-olive-700' : 'text-slate-500'} />
                {loadingSample ? 'Running...' : 'Run Benchmark'}
              </button>
            </>
          )}
          <Link to="/scan" className="btn-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5 shadow-sm">
            <GitBranch size={13} />
            Scan Repository
          </Link>
        </div>
      </div>

      {/* Prominent Alexa+ Voice Cockpit */}
      <AlexaVoiceCockpit />

      {/* Quality Gate hero */}
      {scanData ? (
        <div
          className={`card p-5 flex flex-col md:flex-row md:items-center gap-5 border-l-4 transition-all ${
            isPass
              ? 'border-l-olive-700 bg-white'
              : 'border-l-rose-700 bg-white'
          }`}
        >
          <div className="shrink-0 flex justify-center">
            <ScoreBadge score={greenScore} size="lg" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex flex-wrap items-center gap-2 mb-1.5">
              <span
                className={`inline-flex items-center gap-1 text-[11px] font-mono font-semibold uppercase tracking-wider px-2 py-0.5 rounded ${
                  isPass ? 'bg-olive-50 text-olive-800 border border-olive-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
                }`}
              >
                {isPass ? <ShieldCheck size={13} /> : <ShieldX size={13} />}
                {isPass ? 'Quality Gate: Passed' : 'Quality Gate: Optimization Required'}
              </span>
              <span className="text-xs text-slate-500 font-mono">Pass Threshold: &ge; {threshold}/100</span>
            </div>

            <h2 className="text-base font-bold text-slate-900 leading-snug">
              {isPass
                ? 'Your code complies with green software efficiency standards'
                : `Found ${totalViolations} code pattern${totalViolations !== 1 ? 's' : ''} causing unnecessary energy consumption`}
            </h2>

            <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-slate-600">
              <span className="font-semibold text-slate-800">{totalFiles} scanned files</span>
              <span className="text-slate-300">&middot;</span>
              <span className="font-mono">{totalLines.toLocaleString()} LOC</span>
              {marginalRate !== null && (
                <>
                  <span className="text-slate-300">&middot;</span>
                  <span className="inline-flex items-center gap-1.5 bg-slate-50 px-2 py-0.5 rounded border border-slate-200 font-mono text-[11px]">
                    <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-olive-600' : 'bg-slate-400'}`} />
                    <span className="font-semibold text-slate-700">{activeZone}</span>: {marginalRate} gCO₂/kWh
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
                className="btn-primary flex items-center gap-2 text-xs px-4 py-2.5 shadow-sm"
              >
                <AlertTriangle size={13} />
                Fix {totalViolations} Issue{totalViolations !== 1 ? 's' : ''} with Bedrock AI
                <ArrowRight size={13} />
              </Link>
            ) : (
              <div className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-olive-50 text-olive-900 text-xs font-semibold border border-olive-200 font-mono">
                <CheckCircle2 size={15} className="text-olive-700" />
                No Bottlenecks Detected
              </div>
            )}
          </div>
        </div>
      ) : (
        /* Empty State with 1-click sample demo */
        <div className="card p-10 text-center">
          <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 flex items-center justify-center mx-auto mb-3 text-slate-700">
            <GitBranch size={22} />
          </div>
          <h2 className="text-base font-bold text-slate-900 mb-1">No Active Repository Telemetry</h2>
          <p className="text-xs text-slate-500 max-w-md mx-auto mb-5 leading-relaxed">
            Audit a local codebase, upload a ZIP archive, or link a GitHub repository to evaluate algorithmic energy efficiency, carbon intensity, and synthesize Amazon Bedrock fixes.
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5">
            <button
              onClick={handleScanSample}
              disabled={loadingSample}
              className="btn-secondary flex items-center gap-2 text-xs px-4 py-2 w-full sm:w-auto justify-center"
            >
              <RefreshCw size={13} className={loadingSample ? 'animate-spin text-emerald-600' : 'text-slate-600'} />
              {loadingSample ? 'Analyzing Reference Suite...' : 'Execute Reference Benchmark Suite'}
            </button>
            <Link
              to="/scan"
              className="btn-primary flex items-center gap-2 text-xs px-4 py-2 w-full sm:w-auto justify-center"
            >
              <GitBranch size={13} />
              Audit Repository
            </Link>
          </div>
        </div>
      )}

      {/* Enterprise Cloud Compute & Financial ROI */}
      {scanData && totalViolations > 0 && (
        <div className="card p-4 bg-gradient-to-r from-emerald-50/80 via-white to-olive-50/80 border-emerald-200/90 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-emerald-700 text-white flex items-center justify-center shadow-sm shrink-0">
              <DollarSign size={20} />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider text-emerald-950 flex items-center gap-2">
                Enterprise Cloud Infrastructure ROI
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-100 text-emerald-900 border border-emerald-200 font-mono font-bold">AWS EC2 Projected</span>
              </div>
              <p className="text-xs text-slate-600 mt-0.5">
                Fixing these {totalViolations} algorithmic bottlenecks cuts unnecessary CPU loops, saving an estimated <strong className="text-emerald-900 font-mono">~${(Math.round(((totalViolations * 1.8 * 8760) / 1000) * 0.14 + (totalViolations * 180))).toLocaleString()} / year</strong> across 10 vCPU cloud instances.
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button
              onClick={() => setShowFinOpsModal(true)}
              className="btn-primary text-xs px-3 py-1.5 bg-emerald-700 hover:bg-emerald-800 text-white shadow-sm flex items-center gap-1.5 font-medium"
            >
              <Calculator size={13} />
              Model Cloud ROI
            </button>
            <button
              onClick={() => setShowBotModal(true)}
              className="btn-secondary text-xs px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-800 border-slate-300 shadow-sm flex items-center gap-1.5 font-medium"
            >
              <Bot size={13} className="text-blue-600" />
              Bot PR Action
            </button>
          </div>
        </div>
      )}

      {/* Metrics Grid - 4 distinct non-repeated metrics */}
      {scanData && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Code Issues"
            value={totalViolations}
            subtitle={totalViolations === 0 ? 'Optimal efficiency' : `${totalViolations} patterns flagged`}
            icon={<Activity size={18} />}
            accentColor={totalViolations > 0 ? '#E11D48' : '#384C3B'}
          />
          <MetricCard
            title="Energy Consumed"
            value={energyWh > 0 ? `${(energyWh * 1000).toFixed(2)} mWh` : '—'}
            subtitle="Estimated runtime draw"
            icon={<Zap size={18} />}
            accentColor="#384C3B"
          />
          <MetricCard
            title="Carbon Footprint"
            value={carbonG > 0 ? `${carbonG.toFixed(4)} g` : '—'}
            subtitle={
              marginalRate !== null
                ? `${marginalRate} g/kWh (${activeZone})`
                : 'Regional grid intensity'
            }
            icon={<Leaf size={18} />}
            accentColor="#384C3B"
          />
          <MetricCard
            title="Audited Code Scale"
            value={`${totalFiles} files`}
            subtitle={`${totalLines.toLocaleString()} lines analyzed`}
            icon={<FileCode2 size={18} />}
          />
        </div>
      )}

      {/* Charts & Breakdown */}
      {scanData && scanData.violations?.length > 0 && (
        <div className="grid lg:grid-cols-2 gap-5">
          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="section-title">Top Energy Bottlenecks</h3>
                <p className="text-xs text-slate-500 mt-0.5">Categorized by algorithmic pattern</p>
              </div>
              <Link to="/issues" className="text-xs font-semibold text-olive-800 hover:text-olive-950 flex items-center gap-1">
                Review &amp; Fix <ArrowRight size={12} />
              </Link>
            </div>
            <ViolationChart breakdown={scanData.violation_breakdown} />
          </div>

          <div className="card p-6">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="section-title">Languages in Codebase</h3>
                <p className="text-xs text-slate-500 mt-0.5">Scanned source files distribution</p>
              </div>
              <span className="text-xs text-slate-500 font-mono">
                {scanData.file_results?.length || 0} files
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

      {/* ESG Compliance Audit Certificate Modal */}
      {scanData && (
        <EsgAuditModal
          isOpen={showEsgModal}
          onClose={() => setShowEsgModal(false)}
          scanData={scanData}
          activeZone={activeZone}
          marginalRate={marginalRate}
        />
      )}

      {/* CI/CD & Badges Modal */}
      <CiCdBadgeModal
        isOpen={showCiCdModal}
        onClose={() => setShowCiCdModal(false)}
        repoName={scanData?.repo_path || 'demo-org/ecommerce-api'}
        score={greenScore}
      />

      {/* FinOps & Cloud Cost Calculator Modal */}
      <FinOpsCalculatorModal
        isOpen={showFinOpsModal}
        onClose={() => setShowFinOpsModal(false)}
        violationsCount={totalViolations}
      />

      {/* GitHub PR Bot Interactive Preview Modal */}
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

