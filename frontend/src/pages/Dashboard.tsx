import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { gridService } from '../services/greencodeApi';
import { ScanResult, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
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
  FileCode2,
  FileText,
  DollarSign,
  Bot,
  Code2,
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';
import EsgAuditModal from '../components/common/EsgAuditModal';
import CiCdBadgeModal from '../components/common/CiCdBadgeModal';
import FinOpsCalculatorModal from '../components/common/FinOpsCalculatorModal';
import GitHubBotPreviewModal from '../components/common/GitHubBotPreviewModal';

export default function Dashboard() {
  const t = useT();
  const [scanData, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [isMounting, setIsMounting] = useState(true);
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

  const greenScore = scanData?.green_score ?? 0;
  const isPass = greenScore >= threshold;
  const totalViolations = scanData?.total_violations ?? 0;
  const totalFiles = scanData?.total_files ?? 0;
  const totalLines = scanData?.total_lines ?? 0;
  const energyWh = scanData?.energy_wh ?? 0;
  const carbonG = scanData?.carbon_g ?? 0;
  const marginalRate = gridData?.marginal_carbon_intensity ?? gridData?.carbon_intensity ?? null;
  const isLive = gridData?.is_live ?? false;
  // Language mix is a real, scan-derived fact - no fabricated dollar figures.
  const languagesAnalyzed = Object.keys(scanData?.languages_breakdown || {}).length;
  const topLanguages = Object.entries(scanData?.languages_breakdown || {})
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3)
    .map(([lang]) => lang)
    .join(' · ');

  if (isMounting) {
    return (
      <div className="space-y-5 animate-pulse">
        <div className="h-8 w-56 bg-[var(--gc-bg-subtle)] rounded-lg" />
        <div className="h-28 bg-[var(--gc-bg-subtle)] rounded-xl" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 bg-[var(--gc-bg-subtle)] rounded-lg" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3 pb-1 border-b border-[var(--gc-border-default)]">
        <div className="min-w-0">
          <div className="flex items-center gap-2.5 flex-wrap">
            <h1 className="text-base font-semibold text-[var(--gc-text-primary)] tracking-tight">
              {t('dashboard.title')}
            </h1>
            {scanData && (
              <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-zinc-100 border border-zinc-200/80 text-xs font-mono text-zinc-700 truncate max-w-xs">
                <GitBranch size={12} className="text-zinc-500 shrink-0" />
                <span className="truncate">{scanData.repo_path}</span>
              </span>
            )}
            <span className="hidden sm:inline-block text-[11px] font-mono text-[var(--gc-text-tertiary)]">
              {t('dashboard.standard')}
            </span>
          </div>
        </div>

        {/* Clean Single-Row Action Bar */}
        <div className="flex flex-wrap items-center gap-1.5">
           {scanData && (
             <>
               <Button
                 variant="secondary"
                 size="sm"
                 className="whitespace-nowrap"
                  title={t('dashboard.finopsTooltip')}
                 onClick={() => setShowFinOpsModal(true)}
               >
                 <DollarSign size={13} className="text-emerald-600" />
                 <span>{t('actions.finops')}</span>
               </Button>
               <Button
                 variant="secondary"
                 size="sm"
                 className="whitespace-nowrap"
                  title={t('dashboard.botTooltip')}
                 onClick={() => setShowBotModal(true)}
               >
                 <Bot size={13} className="text-zinc-600" />
                 <span>{t('actions.prBot')}</span>
               </Button>
               <Button
                 variant="secondary"
                 size="sm"
                 className="whitespace-nowrap"
                  title={t('dashboard.esgTooltip')}
                 onClick={() => setShowEsgModal(true)}
               >
                 <FileText size={13} className="text-zinc-600" />
                 <span>{t('actions.esgReport')}</span>
               </Button>
               <Button
                 variant="secondary"
                 size="sm"
                 className="whitespace-nowrap"
                  title={t('dashboard.cicdTooltip')}
                 onClick={() => setShowCiCdModal(true)}
               >
                 <ShieldCheck size={13} className="text-zinc-600" />
                 <span>{t('actions.cicdGate')}</span>
               </Button>
             </>
           )}
          <Button
            asChild
            variant="primary"
            size="sm"
            className="whitespace-nowrap"
          >
            <Link to="/scan">
              <GitBranch size={13} />
              <span>{t('actions.scan')}</span>
            </Link>
          </Button>
        </div>
      </div>

      {/* Row 2: Above-the-Fold Quality Gate Hero + 4 Core Engineering KPIs */}
      {scanData ? (
        <>
        <Card variant="default" padding="lg" className="flex flex-col md:flex-row md:items-center justify-between gap-5">
             <div className="flex items-center gap-5 min-w-0">
              <div className="shrink-0">
                <ScoreBadge score={greenScore} size="md" />
              </div>

              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <Badge
                    variant={isPass ? 'success' : 'critical'}
                    size="sm"
                    className="uppercase tracking-wider text-[10px] px-2 py-0.5"
                  >
                    {isPass ? <ShieldCheck size={12} /> : <ShieldX size={12} />}
                    {isPass ? t('dashboard.gatePassed') : t('dashboard.gateFailed')}
                  </Badge>
                  <span className="text-xs text-zinc-400 font-mono">
                    {t('dashboard.threshold', { threshold })}
                  </span>
                </div>

                <h2 className="text-sm font-semibold text-[var(--gc-text-primary)] leading-snug">
                  {totalViolations === 0
                    ? t('dashboard.noBottlenecks')
                    : t('dashboard.bottlenecks', {
                        count: totalViolations,
                        files: totalFiles,
                        lines: totalLines.toLocaleString(),
                      })}
                </h2>

                <div className="flex flex-wrap items-center gap-2.5 mt-1.5 text-xs text-zinc-500 font-mono">
                  <span>{t('dashboard.files', { count: totalFiles })}</span>
                  <span>&middot;</span>
                  <span>{t('dashboard.lines', { count: totalLines.toLocaleString() })}</span>
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
                 <Button asChild variant="primary" size="sm" className="whitespace-nowrap text-xs">
                   <Link to="/issues" className="flex items-center gap-1.5">
                     <AlertTriangle size={13} className="text-amber-400" />
                     <span>{t('actions.inspectFindings')}</span>
                     <ArrowRight size={13} />
                   </Link>
                  </Button>
                ) : (
                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-50 text-emerald-900 text-xs font-medium border border-emerald-200 font-mono">
                  <CheckCircle2 size={14} className="text-emerald-600" />
                  <span>{t('dashboard.optimal')}</span>
                </div>
              )}
            </div>
          </Card>

          {/* 4 High-Precision Engineering Metric Cards */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <MetricCard
              title={t('dashboard.metricIssues')}
              value={totalViolations}
              subtitle={totalViolations === 0 ? t('dashboard.metricIssuesOk') : t('dashboard.metricIssuesHot', { count: totalViolations })}
              icon={<Activity size={15} />}
              accentColor={totalViolations > 0 ? '#E11D48' : '#059669'}
            />
            <MetricCard
              title={t('dashboard.metricEnergy')}
              value={energyWh > 0 ? `${(energyWh * 1000).toFixed(2)} mWh` : '0.00 mWh'}
              subtitle={t('dashboard.metricEnergySub')}
              icon={<Zap size={15} />}
            />
            <MetricCard
              title={t('dashboard.metricSci')}
              value={carbonG > 0 ? `${carbonG.toFixed(4)} g` : '0.0000 g'}
              subtitle={marginalRate !== null ? t('dashboard.metricSciZone', { rate: marginalRate, zone: activeZone }) : t('dashboard.metricSciSub')}
              icon={<Leaf size={15} />}
            />
            <MetricCard
              title={t('dashboard.metricLangs')}
              value={languagesAnalyzed}
              subtitle={topLanguages || t('dashboard.metricLangsSub')}
              icon={<Code2 size={15} />}
            />
          </div>

          {/* Row 3: Two-Column Engineering Workspace (Findings Table + Rule Breakdown) */}
          <div className="grid lg:grid-cols-12 gap-5 items-start">
            {/* Left 7 Cols: Active Code Efficiency Findings Table */}
            <Card variant="default" className="lg:col-span-7 overflow-hidden border-0 shadow-none">
              <div className="px-5 py-3.5 border-b border-zinc-200/80 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Code2 size={15} className="text-zinc-500" />
                  <h3 className="section-title">{t('dashboard.hotspots')}</h3>
                  <Badge variant="outline" size="sm" className="text-zinc-600 bg-zinc-100 border-zinc-200/80 font-mono">
                    {scanData.violations?.length || 0}
                  </Badge>
                </div>
                <Link
                  to="/issues"
                  className="text-xs font-medium text-emerald-700 hover:text-emerald-800 flex items-center gap-1"
                >
                  <span>{t('actions.openIssues')}</span>
                  <ArrowRight size={12} />
                </Link>
              </div>

              {scanData.violations && scanData.violations.length > 0 ? (
                <div className="divide-y divide-zinc-100">
                  {scanData.violations.slice(0, 5).map((v, idx) => {
                    const sev = (v.severity || 'MEDIUM').toUpperCase();
                    const sevVariant = sev === 'CRITICAL' ? 'critical' : sev === 'HIGH' ? 'high' : sev === 'MEDIUM' ? 'medium' : 'low';
                    return (
                      <div
                        key={`${v.file_path}-${v.line_number}-${idx}`}
                        className="px-5 py-3 hover:bg-zinc-50/80 transition-colors flex items-start justify-between gap-3"
                      >
                        <div className="min-w-0 space-y-1">
                          <div className="flex items-center gap-2">
                            <Badge variant={sevVariant as any} size="sm" className="text-[10px] font-mono font-semibold uppercase tracking-wider">
                              {sev}
                            </Badge>
                            <span className="text-xs font-semibold text-zinc-900 truncate">
                              {v.title || v.violation_type}
                            </span>
                          </div>
                          <div className="text-[11px] font-mono text-zinc-500 truncate">
                            {v.file_path}:{v.line_number}
                          </div>
                        </div>
                        <Button asChild variant="ghost" size="sm" className="text-[11px] font-mono font-medium text-zinc-600 border border-zinc-200 hover:border-zinc-300 hover:bg-white">
                          <Link to="/issues">{t('actions.patch')}</Link>
                        </Button>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="p-8 text-center text-xs text-zinc-500">
                  {t('empty.noIssues')}
                </div>
              )}
            </Card>

            {/* Right 5 Cols: Algorithmic Breakdown & Language Distribution */}
            <div className="lg:col-span-5 space-y-5">
              <Card variant="default" padding="lg">
                <div className="mb-3">
                  <h3 className="section-title">{t('dashboard.ruleBreakdown')}</h3>
                  <p className="text-[11px] text-[var(--gc-text-tertiary)] mt-0.5">
                    {t('dashboard.ruleHint')}
                  </p>
                </div>
                <ViolationChart breakdown={scanData.violation_breakdown} />
              </Card>

              {scanData.file_results && scanData.file_results.length > 0 && (
                <Card variant="default" padding="lg">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="section-title">{t('dashboard.languages')}</h3>
                    <span className="text-[11px] font-mono text-zinc-500">
                      <FileCode2 size={12} className="inline mr-1" />
                      <span>{t('dashboard.fileResults', { count: scanData.file_results.length })}</span>
                    </span>
                  </div>
                  <LanguageBreakdown fileResults={scanData.file_results} />
                </Card>
              )}
            </div>
          </div>
        </>
      ) : (
        /* Empty State */
        <Card variant="default" padding="lg" className="text-center">
          <div className="w-11 h-11 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center mx-auto mb-3 text-zinc-700">
            <GitBranch size={20} />
          </div>
          <h2 className="text-sm font-semibold text-[var(--gc-text-primary)] mb-1">{t('empty.noScanTitle')}</h2>
          <p className="text-xs text-[var(--gc-text-tertiary)] max-w-md mx-auto mb-5 leading-relaxed">
            {t('empty.noScanBody')}
          </p>
          <div className="flex flex-col sm:flex-row items-center justify-center gap-2.5">
            <Button asChild variant="primary" size="md" className="text-xs">
              <Link to="/scan" className="flex items-center gap-2">
                <GitBranch size={13} />
                <span>{t('actions.scan')}</span>
              </Link>
            </Button>
          </div>
        </Card>
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
  const t = useT();
  const langCount: Record<string, number> = {};
  fileResults.forEach((f) => {
    const lang = f.language || t('dashboard.unknownLanguage');
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
              {count} {count === 1 ? t('dashboard.file') : t('dashboard.filesLabel')}
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
