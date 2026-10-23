import { useState } from 'react';
import { Link } from 'react-router-dom';
import { refactorService, githubService } from '../services/greencodeApi';
import { ScanResult, Violation } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { IssueCard } from '../components/common/IssueCard';
import CodeDiffViewer from '../components/common/CodeDiffViewer';
import { VIOLATION_RULE_MAP } from '../types';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import { Modal } from '../components/primitives/Modal';
import {
  Search, Zap, Github, Copy, GitBranch, RefreshCw,
  CheckCircle, Loader2, AlertCircle, ExternalLink, X, ArrowUpRight
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';

export default function Issues() {
  const t = useT();
  const [scanData]        = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [searchQuery, setSearchQuery]       = useState('');
  const [severityFilter, setSeverityFilter] = useState('All');
  const [sortOrder, setSortOrder]           = useState('highest_penalty');
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);
  const [refactorResults, setRefactorResults] = useState<Record<string, any>>({});
  const [refactorErrors, setRefactorErrors] = useState<Record<string, string>>({});
  const [refactoring, setRefactoring]       = useState<Set<string>>(new Set());
  const [batchRefactoring, setBatchRefactoring] = useState(false);
  const [batchProgress, setBatchProgress]   = useState<{ done: number; total: number } | null>(null);
  const [prResults, setPrResults]           = useState<Record<string, { url?: string; error?: string }>>({});
  const [prLoading, setPrLoading]           = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey]           = useState<string | null>(null);

  // PR Modal state for entering or confirming GitHub details
  const [prModalViolation, setPrModalViolation] = useState<{ violation: Violation; key: string } | null>(null);
  const [prModalRepo, setPrModalRepo]       = useState('');
  const [prModalError, setPrModalError]     = useState<string | null>(null);
  const [copyError, setCopyError] = useState<string | null>(null);

  const violations: Violation[] = scanData?.violations || [];

  const SEVERITIES   = ['All', 'CRITICAL', 'HIGH', 'MEDIUM'];
  const SORT_OPTIONS = [
    { value: t('issues.sort.highestPenalty'), key: 'highest_penalty' },
    { value: t('issues.sort.severity'), key: 'severity' },
    { value: t('issues.sort.fileName'), key: 'file_name' },
  ];

  const filteredViolations = violations.filter(v => {
    const matchesSeverity = severityFilter === 'All' || v.severity === severityFilter;
    const q = searchQuery.toLowerCase();
    const ruleCode = VIOLATION_RULE_MAP[v.violation_type] || 'GSF-S999';
    const corpus = `${v.title} ${v.description} ${v.file_path} ${v.violation_type} ${ruleCode} ${v.gsf_pattern}`.toLowerCase();
    return matchesSeverity && (!q || corpus.includes(q));
  });

   const sortedViolations = [...filteredViolations].sort((a, b) => {
     if (sortOrder === 'highest_penalty') return b.deduction - a.deduction;
     if (sortOrder === 'severity') {
       const rank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
       return (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9);
     }
     return a.file_path.localeCompare(b.file_path);
   });

   const activeViolation =
     sortedViolations.find((violation) =>
       violation.file_path === selectedViolation?.file_path &&
       violation.line_number === selectedViolation?.line_number
     ) || sortedViolations[0] || null;

  const getViolationKey = (v: Violation, idx: number) => {
    return `${v.file_path}-${v.line_number}-${v.violation_type}-${idx}`;
  };

  // Helper to extract GitHub slug from scanData
  const getDetectedGitHubSlug = (): string => {
    if (!scanData) return '';
    const raw = scanData.repo_path || '';
    const clean = raw
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();
    if (/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(clean)) {
      return clean;
    }
    return '';
  };

  const handleRefactor = async (violation: Violation, key: string) => {
    if (refactorResults[key]) return;

    const snippet = (violation.snippet || '').trim();
    if (!snippet) {
      setRefactorErrors((previous) => ({
        ...previous,
        [key]: 'The audit did not return source code for this finding, so it cannot be safely refactored.',
      }));
      return;
    }

    setRefactorErrors((previous) => ({ ...previous, [key]: '' }));
    setRefactoring(p => new Set(p).add(key));
    try {
      const resp = await refactorService.refactor(
        snippet,
        violation.violation_type,
        violation.language || 'python',
        violation.context_code || undefined
      );
      if (
        typeof resp.data.original_code !== 'string' ||
        !resp.data.original_code.trim() ||
        typeof resp.data.refactored_code !== 'string' ||
        !resp.data.refactored_code.trim()
      ) {
        throw new Error('The refactoring service returned an incomplete code diff.');
      }
      setRefactorResults(p => ({ ...p, [key]: resp.data }));
    } catch (err: any) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        'The refactoring request failed. Check the API configuration and try again.';
      setRefactorErrors((previous) => ({ ...previous, [key]: message }));
    } finally {
      setRefactoring(p => { const s = new Set(p); s.delete(key); return s; });
    }
  };

  const handleBatchRefactor = async () => {
    const unrefactored = sortedViolations
      .map((v, i) => ({ v, key: getViolationKey(v, i) }))
      .filter(({ key }) => !refactorResults[key]);

    if (unrefactored.length === 0) return;

    setBatchRefactoring(true);
    setBatchProgress({ done: 0, total: unrefactored.length });

    for (let i = 0; i < unrefactored.length; i++) {
      const { v, key } = unrefactored[i];
      await handleRefactor(v, key);
      setBatchProgress({ done: i + 1, total: unrefactored.length });
    }

    setBatchRefactoring(false);
    setBatchProgress(null);
  };

  const initiatePR = (violation: Violation, key: string) => {
    const detectedSlug = getDetectedGitHubSlug();
    if (!detectedSlug) {
      setPrResults((previous) => ({
        ...previous,
        [key]: { error: 'Pull requests can only be created for a completed GitHub repository audit.' },
      }));
      return;
    }
    setPrModalViolation({ violation, key });
    setPrModalRepo(detectedSlug);
    setPrModalError(null);
  };

  const submitPR = async () => {
    if (!prModalViolation) return;
    const { violation, key } = prModalViolation;
    const result = refactorResults[key];
    if (!result) return;

    const cleanRepo = prModalRepo
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();

    if (!/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(cleanRepo)) {
      setPrModalError('Please enter a valid GitHub repository in "owner/repo" format.');
      return;
    }
    if (cleanRepo !== getDetectedGitHubSlug()) {
      setPrModalError('Pull requests must target the repository that was audited.');
      return;
    }

    setPrLoading(p => new Set(p).add(key));
    setPrModalError(null);

    try {
      const resp = await githubService.createPullRequest(
        cleanRepo,
        violation.relative_path || violation.file_path,
        result.refactored_code,
        violation.title,
        result.energy_reduction_pct,
        result.carbon_saved_gco2_10k_runs,
        result.original_code || violation.snippet || undefined
      );

      const prUrl = resp.data?.pr_url;
      if (!resp.data?.success || typeof prUrl !== 'string' || !prUrl) {
        throw new Error('GitHub did not confirm pull request creation.');
      }
      setPrResults(p => ({ ...p, [key]: { url: prUrl } }));
      setPrModalViolation(null);

      window.open(prUrl, '_blank');
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to create Pull Request. Verify repository permissions.';
      setPrModalError(msg);
      setPrResults(p => ({ ...p, [key]: { error: msg } }));
    } finally {
      setPrLoading(p => { const s = new Set(p); s.delete(key); return s; });
    }
  };

  const handleCopy = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopyError(null);
      setCopiedKey(key);
      window.setTimeout(() => setCopiedKey(null), 1500);
    } catch {
      setCopyError(t('issues.copyFailed'));
    }
  };

  if (!scanData) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-12 h-12 rounded-xl bg-zinc-100 border border-zinc-200 flex items-center justify-center mb-3 text-zinc-700">
          <GitBranch size={20} />
        </div>
        <h2 className="text-base font-semibold text-zinc-900 dark:text-zinc-100 mb-1">{t('issues.noActiveScan')}</h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400 mb-5 max-w-sm">
          {t('issues.noActiveScanBody')}
        </p>
        <Button asChild variant="primary" size="md">
          <Link to="/scan" className="flex items-center gap-2 text-xs">
            <RefreshCw size={13} /> {t('issues.scanRepositoryBtn')}
          </Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="gc-issues-page space-y-4">

      <section className="gc-audit-metrics" aria-label="Audit summary">
        <article className="gc-metric-card gc-metric-score">
          <span className="gc-metric-label">{t('issues.metrics.greenScore')}</span>
          <strong>{Math.round(scanData.green_score)}<small>/100</small></strong>
          <span className="gc-metric-note">{t('issues.metrics.efficiencyRating')}</span>
        </article>
        <article className="gc-metric-card">
          <span className="gc-metric-label">{t('issues.metrics.findings')}</span>
          <strong>{violations.length.toLocaleString()}</strong>
          <span className="gc-metric-note">
            {t('issues.metrics.highPriority', {
              count: violations.filter((violation) => violation.severity === 'CRITICAL' || violation.severity === 'HIGH').length.toLocaleString(),
            })}
          </span>
        </article>
        <article className="gc-metric-card">
          <span className="gc-metric-label">{t('issues.metrics.filesAnalyzed')}</span>
          <strong>{scanData.total_files.toLocaleString()}</strong>
          <span className="gc-metric-note">{t('issues.metrics.sourceLines', { count: scanData.total_lines.toLocaleString() })}</span>
        </article>
        <article className="gc-metric-card">
          <span className="gc-metric-label">{t('issues.metrics.carbonImpact')}</span>
          <strong className="gc-metric-value">
            {typeof scanData.carbon_g === 'number' && Number.isFinite(scanData.carbon_g)
              ? `${scanData.carbon_g.toFixed(3)} g`
              : t('issues.metrics.notMeasured')}
          </strong>
          <span className="gc-metric-note">
            {typeof scanData.energy_wh === 'number' && Number.isFinite(scanData.energy_wh)
              ? t('issues.metrics.energyEstimate', { amount: scanData.energy_wh.toFixed(3) })
              : t('issues.metrics.noEstimate')}
          </span>
        </article>
      </section>

      {/* Header */}
      <div className="gc-issues-heading flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 border-b border-zinc-200/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
             <h1 className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 tracking-tight">{t('issues.pageTitle')}</h1>
             <Badge variant="olive" className="py-1">{t('issues.engine')}</Badge>
           </div>
           <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
             {t('issues.findingsSummary', {
               count: String(violations.length),
               plural: violations.length !== 1 ? 's' : '',
               files: String(scanData.total_files),
               repo: scanData.repo_path || ''
              })}
            </p>
          </div>
        {sortedViolations.length > 0 && (
          <Button
            variant="primary"
            size="sm"
            className="whitespace-nowrap"
            onClick={handleBatchRefactor}
            disabled={batchRefactoring}
          >
            {batchRefactoring ? (
              <>
                <Loader2 size={13} className="animate-spin text-emerald-400" />
                <span>{t('issues.synthesizingAll', { done: String(batchProgress?.done), total: String(batchProgress?.total) })}</span>
               </>
             ) : (
               <>
                 <Zap size={13} className="text-emerald-400" />
                 <span>{t('issues.synthesizeAll')}</span>
              </>
            )}
          </Button>
        )}
      </div>

      {copyError && <p role="alert" className="rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-xs text-rose-700">{copyError}</p>}

       {/* Filters Toolbar */}
       <div className="flex flex-col sm:flex-row gap-3">
         <div className="relative flex-1">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 dark:text-zinc-500" size={15} />
           <Input
             type="text"
              placeholder={t('issues.searchPlaceholder')}
             className="text-xs py-2.5 pl-10"
             value={searchQuery}
             onChange={e => setSearchQuery(e.target.value)}
           />
         </div>
         <Select
           className="w-full sm:w-48 text-xs py-2.5 font-medium"
           value={severityFilter}
           onChange={e => setSeverityFilter(e.target.value)}
          >
            {SEVERITIES.map(s => (
              <option key={s} value={s}>{s === 'All' ? t('issues.allSeverities') : t('issues.severityOption', { severity: t(`severity.${s}`) })}</option>
            ))}
          </Select>
          <Select
            className="w-full sm:w-48 text-xs py-2.5 font-medium"
            value={sortOrder}
            onChange={e => setSortOrder(e.target.value)}
          >
            {SORT_OPTIONS.map(s => <option key={s.key} value={s.key}>{s.value}</option>)}
         </Select>
       </div>

      {/* Subheader status count */}
        <div className="flex items-center justify-between text-xs text-slate-500 dark:text-zinc-400 px-0.5">
          <div className="flex items-center gap-2 font-medium">
            <span dangerouslySetInnerHTML={{ __html: t('issues.showingCount', { shown: String(filteredViolations.length), total: String(violations.length) }) }} />
            {searchQuery && (
              <button onClick={() => setSearchQuery('')} className="text-emerald-700 hover:text-emerald-900 font-bold ml-1">
                {t('issues.clearSearch')}
              </button>
            )}
          </div>
          <span className="text-slate-400 dark:text-zinc-400 font-mono text-[11px]">{t('issues.patternCatalogue')}</span>
        </div>

        {/* Issues List */}
        {sortedViolations.length === 0 ? (
          <Card variant="default" padding="lg" className="text-center border-slate-200/80 dark:border-zinc-700 shadow-xs">
            <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
              <CheckCircle size={22} />
            </div>
            <h3 className="font-bold text-slate-800 dark:text-zinc-100 mb-1">{t('issues.noMatchTitle')}</h3>
            <p className="text-xs text-slate-500 dark:text-zinc-400">{t('issues.noMatchBody')}</p>
        </Card>
      ) : (
        <div className="gc-issues-workbench">
          <aside className="gc-issues-list" aria-label={t('issues.findingsList')}>
            {sortedViolations.map((v, idx) => {
              const key = getViolationKey(v, idx);
              const isSelected =
                activeViolation?.file_path === v.file_path &&
                activeViolation?.line_number === v.line_number;
              return (
                <IssueCard
                  key={key}
                  violation={{ ...v, rule_code: VIOLATION_RULE_MAP[v.violation_type] || 'GSF-S999' }}
                  onClick={() => setSelectedViolation(v)}
                  isSelected={isSelected}
                />
              );
            })}
          </aside>

          <section className="gc-issue-detail" aria-label={t('issues.selectedFinding')}>
          {sortedViolations.map((v, idx) => {
            const key = getViolationKey(v, idx);
            const isRefactoring    = refactoring.has(key);
            const refactorResult   = refactorResults[key];
            const isPrLoading      = prLoading.has(key);
            const prResult         = prResults[key];
            const isSelected       =
              activeViolation?.file_path === v.file_path &&
              activeViolation?.line_number === v.line_number;

            if (!isSelected) return null;
            return (
              <div key={key} className="space-y-3">
                <IssueCard
                  violation={{ ...v, rule_code: VIOLATION_RULE_MAP[v.violation_type] || 'GSF-S999' }}
                  onClick={() => setSelectedViolation(v)}
                  isSelected={isSelected}
                />

                 {refactorResult ? (
                   <Card variant="default" padding="lg" className="ml-2 sm:ml-4 border-emerald-300 shadow-xs bg-white space-y-4">
                     <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                       <div className="flex items-center gap-2">
                         <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <h3 className="font-bold text-xs uppercase tracking-wider text-slate-800 dark:text-zinc-200">
                            {t('issues.ecoRefactoring')}
                          </h3>
                           <Badge
                            variant="outline"
                            size="sm"
                            title={refactorResult.model_used || undefined}
                            className="max-w-[16rem] truncate text-[10px] bg-slate-900 text-emerald-400 border-slate-800 font-mono"
                          >
                            {refactorResult.model_used || t('issues.providerUnreported')}
                         </Badge>
                       </div>
                       <Button
                         variant="ghost"
                         size="xs"
                         className="text-xs"
                         onClick={() => handleCopy(refactorResult.refactored_code, `copy-${key}`)}
                       >
                         {copiedKey === `copy-${key}` ? (
                           <>
                             <CheckCircle size={13} className="text-emerald-600" />
                            <span className="text-emerald-800 font-bold">{t('actions.copied')}</span>
                            </>
                          ) : (
                            <>
                              <Copy size={13} />
                              <span>{t('codeDiff.copyPatch')}</span>
                           </>
                         )}
                       </Button>
                     </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="card-inset p-3 text-center bg-slate-50/80">
                         <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">
                           {t('issues.energyReduction')}
                         </p>
                        <p className="text-2xl font-black text-emerald-600">
                          -{refactorResult.energy_reduction_pct}%
                        </p>
                      </div>
                      <div className="card-inset p-3 text-center bg-slate-50/80">
                         <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">
                           {t('issues.co2Saved')}
                         </p>
                        <p className="text-2xl font-black text-emerald-700">
                          {refactorResult.carbon_saved_gco2_10k_runs} g
                        </p>
                      </div>
                    </div>

                    {refactorResult.explanation && (
                      <p className="text-xs text-slate-600 leading-relaxed bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/70">
                        {refactorResult.explanation}
                      </p>
                    )}

                    <CodeDiffViewer
                      originalCode={refactorResult.original_code}
                      refactoredCode={refactorResult.refactored_code}
                      language={v.language || 'python'}
                    />

                    {/* PR result indicator */}
                    {prResult?.url && (
                      <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800">
                        <span className="flex items-center gap-2 font-medium">
                          <CheckCircle size={15} className="text-emerald-600" />
                          {t('issues.prOpened')}
                        </span>
                        <a
                          href={prResult.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 font-bold underline hover:text-emerald-950"
                        >
                          {t('issues.viewPr')} <ArrowUpRight size={13} />
                        </a>
                      </div>
                    )}

                    {prResult?.error && (
                      <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2">
                        <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{prResult.error}</span>
                      </div>
                    )}

                    {/* Action buttons */}
                     <div className="flex flex-wrap gap-2.5 pt-3 border-t border-slate-200/80">
                       <Button
                         variant="primary"
                         size="sm"
                         className="shadow-xs"
                         onClick={() => initiatePR(v, key)}
                         disabled={isPrLoading}
                       >
                          {isPrLoading ? (
                            <>
                              <Loader2 size={13} className="animate-spin" /> {t('issues.committingPr')}
                            </>
                          ) : (
                            <>
                              <Github size={13} /> {t('issues.openPr')}
                            </>
                          )}
                       </Button>

                       <Button
                         variant="secondary"
                         size="sm"
                         className="shadow-xs"
                         onClick={() => handleCopy(refactorResult.refactored_code, `btn-${key}`)}
                       >
                          {copiedKey === `btn-${key}` ? (
                            <>
                              <CheckCircle size={13} className="text-emerald-600" /> {t('actions.copied')} Code
                            </>
                          ) : (
                            <>
                              <Copy size={13} /> {t('issues.copyRefactored')}
                            </>
                          )}
                       </Button>

                       {refactorResult.unified_diff && (
                         <Button
                           variant="secondary"
                           size="sm"
                           className="shadow-xs"
                           onClick={() => handleCopy(refactorResult.unified_diff, `diff-${key}`)}
                         >
                            {copiedKey === `diff-${key}` ? (
                              <>
                                <CheckCircle size={13} className="text-emerald-600" /> {t('actions.copied')} .diff
                              </>
                            ) : (
                              <>
                                <Copy size={13} /> {t('issues.copyDiff')}
                              </>
                            )}
                         </Button>
                       )}

                       {refactorResult.github_suggestion_markdown && (
                         <Button
                           variant="secondary"
                           size="sm"
                           className="shadow-xs"
                           onClick={() => handleCopy(refactorResult.github_suggestion_markdown, `sug-${key}`)}
                         >
                            {copiedKey === `sug-${key}` ? (
                              <>
                                <CheckCircle size={13} className="text-emerald-600" /> {t('issues.copiedSuggestion')}
                              </>
                            ) : (
                              <>
                                <Copy size={13} /> {t('issues.copyPrSuggestion')}
                              </>
                            )}
                         </Button>
                       )}
                     </div>
                   </Card>
                 ) : isRefactoring ? (
                   <Card variant="default" padding="md" className="ml-2 sm:ml-4 bg-slate-50 border-emerald-200 shadow-xs">
                     <div className="flex items-center gap-2.5 text-xs text-slate-700 font-medium">
                       <Loader2 size={15} className="animate-spin text-emerald-600" />
                       <span>{t('issues.synthesizingPatch', { file: v.title })}...</span>
                       <Badge variant="outline" size="sm" className="text-[10px] bg-slate-900 text-emerald-400 border-slate-800 font-mono">
                         {t('issues.bedrockPreferred')}
                       </Badge>
                     </div>
                   </Card>
                 ) : (
                   <div className="ml-2 sm:ml-4">
                     {refactorErrors[key] && (
                       <div role="alert" className="mb-2 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-xs text-rose-700">
                         <AlertCircle size={14} className="mt-0.5 shrink-0" />
                         <span>{refactorErrors[key]}</span>
                       </div>
                     )}
                     <Button
                       variant="secondary"
                       size="sm"
                       className="hover:border-emerald-400 hover:text-emerald-800"
                       onClick={() => handleRefactor(v, key)}
                     >
                        <Zap size={13} className="text-amber-500" /> {t('issues.synthesizeFix')}
                     </Button>
                   </div>
                 )}
              </div>
            );
          })}
          </section>
        </div>
      )}

      {/* GitHub PR Modal Dialog */}
      <Modal
        isOpen={!!prModalViolation}
        onClose={() => setPrModalViolation(null)}
        showCloseButton={false}
        size="md"
        overlayClassName="items-center bg-slate-900/40"
        className="!max-w-lg rounded-2xl border-slate-200 shadow-xl"
        contentClassName="p-0 overflow-visible"
        footer={
          <div className="flex items-center justify-end gap-2.5">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setPrModalViolation(null)}
            >
              {t('actions.cancel')}
            </Button>
            <Button
              type="button"
              variant="primary"
              size="sm"
              disabled={prLoading.has(prModalViolation?.key || '')}
              onClick={submitPR}
            >
                {prLoading.has(prModalViolation?.key || '') ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> {t('issues.creatingPr')}
                  </>
                ) : (
                  <>
                    <ExternalLink size={13} /> {t('issues.openPr')}
                  </>
                )}
            </Button>
          </div>
        }
      >
        <div className="px-6 py-4 border-b border-slate-100 dark:border-zinc-700 flex items-center justify-between">
          <div className="flex items-center gap-2 text-slate-900 dark:text-zinc-100 font-bold text-sm">
            <Github size={18} />
            <span>{t('issues.createPr')}</span>
          </div>
          <button
            onClick={() => setPrModalViolation(null)}
            className="text-slate-400 dark:text-zinc-500 hover:text-slate-600 dark:hover:text-zinc-300 p-1"
          >
            <X size={16} />
          </button>
        </div>

        {prModalError && (
          <div className="px-6 py-4 bg-red-50 border-b border-red-200 text-xs text-red-700 flex items-start gap-2">
            <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
            <span className="leading-relaxed font-medium">{prModalError}</span>
          </div>
        )}

        <div className="px-6 py-4 space-y-4 text-xs">
          <div>
            <label className="block font-bold text-slate-700 dark:text-zinc-300 mb-1 uppercase tracking-wider">
              {t('issues.targetRepo')}
            </label>
            <Input
              type="text"
              className="text-xs font-mono opacity-70"
              value={prModalRepo}
              readOnly
            />
            <p className="text-[11px] text-slate-400 dark:text-zinc-500 mt-1">
              {t('issues.targetRepoHelp')}
            </p>
          </div>

          <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg space-y-1">
            <p className="text-[11px] font-bold text-slate-700 dark:text-zinc-300">{t('issues.patchDetails')}</p>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono truncate">
              {t('issues.fileLabel', { path: prModalViolation?.violation.file_path || '' })}
            </p>
            <p className="text-[11px] text-slate-500 dark:text-zinc-400">
                {t('issues.remediationLabel', { title: prModalViolation?.violation.title || '' })}
              </p>
            </div>
        </div>
      </Modal>

    </div>
  );
}
