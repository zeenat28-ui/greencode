import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { scanService } from '../services/greencodeApi';
import { authHeaders } from '../services/api';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { RepositoryRecord, RepositoryPage, ScanResult } from '../types';
import ScoreBadge from '../components/common/ScoreBadge';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import {
  Calendar, ExternalLink, RefreshCw, GitBranch, Search,
  Eye, RotateCw, Leaf, Zap, AlertTriangle, FolderGit2,
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';

export default function History() {
  const navigate = useNavigate();
  const t = useT();
  const [historyData, setHistoryData] = useLocalStorage<RepositoryPage | null>('greencode_history', null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [searchTerm, setSearchTerm] = useState('');
  const [rescanningId, setRescanningId] = useState<number | null>(null);
  const [rescanError, setRescanError] = useState<string | null>(null);

  useEffect(() => {
    loadHistory();
  }, []);

  const loadHistory = async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true);
    else setLoading(true);
    setHistoryError(null);
    try {
      const resp = await scanService.getHistory();
      setHistoryData(resp.data);
    } catch (err: any) {
      setHistoryError(
        err?.response?.data?.detail ||
          err?.message ||
          t('history.loadError')
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /**
   * Re-run a stored audit (routes local_workspace records to /api/scan/local-workspace
   * and GitHub repositories to /api/scan/github).
   */
  const handleRescan = async (record: RepositoryRecord) => {
    const isLocal = record.source === 'local_workspace';
    const slug = isLocal
      ? record.path_or_url
      : record.full_name || record.path_or_url;
    if (!slug) {
      setRescanError('This record has no repository reference.');
      return;
    }
    setRescanningId(record.id);
    setRescanError(null);
    try {
      if (isLocal) {
        const prefix = 'local-workspace/';
        if (!slug.startsWith(prefix)) {
          throw new Error('This local audit does not include a valid workspace path and cannot be re-run.');
        }
        const subpath = slug.slice(prefix.length);
        const res = await fetch('/api/scan/local-workspace', {
          method: 'POST',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({ subpath, repo_name: record.name }),
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body?.detail || `Could not re-audit local path ${subpath}`);
        }
        const data = await res.json();
        setScanData(data);
      } else {
        const resp = await scanService.scanGitHub(slug, record.default_branch || undefined);
        setScanData(resp.data);
      }
      await loadHistory(true);
      navigate('/issues');
    } catch (err: any) {
      setRescanError(
        err?.response?.data?.detail ||
          err?.message ||
          `Could not re-audit ${slug}. Verify the repository still exists and is accessible.`
      );
    } finally {
      setRescanningId(null);
    }
  };

  /** Load a stored audit into the active session, hydrating stored violations from the backend. */
  const handleViewRecord = async (record: RepositoryRecord) => {
    let hydrated: any;
    try {
      const resp = await scanService.getRepositoryDetails(record.id);
      hydrated = resp.data;
    } catch (err: any) {
      setRescanError(
        err?.response?.data?.detail ||
          err?.message ||
          'Could not load the saved audit details.'
      );
      return;
    }

    const rawViolations = Array.isArray(hydrated.violations) ? hydrated.violations : [];
    const breakdown: Record<string, number> = {};
    for (const v of rawViolations) {
      const vt = v.violation_type || 'UNKNOWN';
      breakdown[vt] = (breakdown[vt] || 0) + 1;
    }

    const isLocal =
      hydrated.source === 'local_workspace' ||
      String(hydrated.full_name || hydrated.path_or_url || '').startsWith('local-workspace/');

    const loadedScan: ScanResult = {
      repo_path: hydrated.full_name || hydrated.path_or_url || hydrated.name,
      repo_id: hydrated.id,
      full_name: hydrated.full_name || undefined,
      default_branch: hydrated.default_branch || undefined,
      html_url: hydrated.html_url || undefined,
      source: isLocal ? 'local_workspace' : 'github',
      is_github: !isLocal,
      total_files: hydrated.total_files || 0,
      total_lines: hydrated.total_lines || 0,
      green_score: hydrated.green_score || 0,
      total_violations: rawViolations.length || (record as any).total_violations || 0,
      violation_breakdown: hydrated.violation_breakdown || breakdown,
      languages_breakdown: hydrated.languages_breakdown || {},
      violations: rawViolations,
      file_results: hydrated.file_results || [],
    };

    setScanData(loadedScan);
    navigate('/issues');
  };

  const records: RepositoryRecord[] = historyData?.repositories || [];
  const filteredRecords = records.filter((r) => {
    const q = searchTerm.toLowerCase();
    return (
      (r.name && r.name.toLowerCase().includes(q)) ||
      (r.full_name && r.full_name.toLowerCase().includes(q)) ||
      (r.path_or_url && r.path_or_url.toLowerCase().includes(q))
    );
  });

  const cumulative = historyData?.cumulative_savings;
  const avgScore = records.length
    ? Math.round(records.reduce((acc, r) => acc + (r.green_score || 0), 0) / records.length)
    : 0;

  if (loading && !historyData) {
    return (
      <div className="flex flex-col items-center justify-center py-28 text-slate-500 dark:text-slate-400">
        <RefreshCw size={28} className="animate-spin text-emerald-600 mb-3" />
        <p className="text-sm font-medium">{t('history.loadingRecords')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
       <div className="flex items-center gap-2 mb-1">
            <Badge variant="olive">{t('history.badge')}</Badge>
            <span className="text-[11px] font-mono font-medium text-slate-500 dark:text-slate-400">{t('history.subtitle')}</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 dark:text-slate-100 tracking-tight">{t('history.title')}</h1>
          <p className="text-sm text-slate-600 dark:text-slate-400 mt-0.5">
            {t('history.description')}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <Button
            onClick={() => loadHistory(true)}
            disabled={refreshing || loading}
            variant="secondary"
            size="sm"
            className="text-xs font-semibold shadow-sm"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin text-olive-700' : ''} />
            {refreshing ? t('history.refreshing') : t('history.refreshButton')}
          </Button>
          <Button asChild variant="primary" size="sm" className="text-xs font-semibold shadow-sm">
            <Link to="/scan">
              <GitBranch size={13} />
              {t('history.newAudit')}
            </Link>
          </Button>
        </div>
      </div>

      {/* Rescan Error Notice */}
      {rescanError && (
        <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 flex items-start gap-3 text-red-900 dark:text-red-200 text-sm">
          <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold">{t('history.rescanError')}</p>
            <p className="text-xs text-red-700 dark:text-red-300 mt-0.5">{rescanError}</p>
          </div>
          <button
            onClick={() => setRescanError(null)}
            className="text-xs text-red-700 dark:text-red-300 hover:text-red-900 dark:hover:text-red-100 underline font-semibold"
          >
            {t('history.dismissError')}
          </button>
        </div>
      )}

      {historyError && (
        <div role="alert" className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm">
          <p className="font-bold">{t('history.loadError')}</p>
          <p className="text-xs mt-1">{historyError}</p>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card padding="lg">
          <p className="label mb-1">{t('history.kpi.repositoriesAudited')}</p>
          <p className="text-2xl font-black text-slate-900 dark:text-slate-100">{records.length}</p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('history.kpi.archivedAudits')}</p>
        </Card>
        <Card padding="lg">
          <p className="label mb-1">{t('history.kpi.avgGreenScore')}</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-black text-olive-800">{records.length ? avgScore : '—'}</p>
            {records.length > 0 && (
              <Badge variant={avgScore >= threshold ? 'success' : 'critical'} className="text-[10px] px-2 py-0.5 rounded-full">
                {avgScore >= threshold ? t('history.kpi.passed') : t('history.kpi.needsReview')}
              </Badge>
            )}
          </div>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('history.kpi.passThreshold', { threshold })}</p>
        </Card>
        <Card padding="lg">
          <p className="label mb-1">{t('history.kpi.carbonAbated')}</p>
          <p className="text-2xl font-black text-olive-800 flex items-center gap-1.5">
            <Leaf size={18} className="text-olive-700" />
            {cumulative?.total_carbon_saved_gco2_10k_runs != null
              ? `${cumulative.total_carbon_saved_gco2_10k_runs.toFixed(1)} g`
              : '0.0 g'}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{t('history.kpi.savingsPer10k')}</p>
        </Card>
        <Card padding="lg">
          <p className="label mb-1">{t('history.kpi.aiFixes')}</p>
          <p className="text-2xl font-black text-blue-700 flex items-center gap-1.5">
            <Zap size={18} className="text-blue-600" />
            {cumulative?.total_refactoring_operations ?? 0}
          </p>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            {cumulative?.average_energy_reduction_pct != null
              ? t('history.kpi.avgEnergyCut', { pct: cumulative.average_energy_reduction_pct.toFixed(0) })
              : t('history.kpi.bedrockOptimizations')}
          </p>
        </Card>
      </div>

      {records.length === 0 ? (
        <Card padding="none" className="p-14 text-center">
          <div className="w-14 h-14 rounded-2xl bg-olive-50 border border-olive-200 flex items-center justify-center mx-auto mb-4 text-olive-800 shadow-sm">
            <FolderGit2 size={26} />
          </div>
          <h3 className="font-bold text-slate-900 dark:text-slate-100 text-base mb-1">{t('history.empty.title')}</h3>
          <p className="text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto mb-6">
            {t('history.empty.description')}
          </p>
          <Button asChild variant="primary" className="inline-flex items-center gap-2">
            <Link to="/scan">
              <GitBranch size={15} /> {t('history.empty.runFirstAudit')}
            </Link>
          </Button>
        </Card>
      ) : (
        <Card padding="none" className="overflow-hidden max-w-full">
          {/* Table Toolbar */}
          <div className="p-4 border-b border-slate-200/80 bg-slate-50/70 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative w-full sm:w-80">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <Input
                type="text"
                placeholder={t('history.searchPlaceholder')}
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="pl-9 py-2 text-xs w-full bg-white dark:bg-slate-800 focus:ring-olive-600 focus:border-olive-600"
              />
            </div>
            <span className="text-xs text-slate-600 dark:text-slate-400 font-medium">
              {t('history.showingRecords', { shown: filteredRecords.length, total: records.length })}
            </span>
          </div>

          <div className="overflow-x-auto max-w-full">
            <table className="w-full text-sm text-left min-w-[600px]">
              <thead className="bg-slate-50 dark:bg-slate-800 border-b border-slate-200/80 dark:border-slate-700 text-slate-500 dark:text-slate-400 text-xs font-semibold">
                <tr>
                  <th className="label px-4 py-3.5">{t('history.table.columns.repositoryIdentifier')}</th>
                  <th className="label px-4 py-3.5">{t('history.table.columns.greenScore')}</th>
                  <th className="label px-4 py-3.5">{t('history.table.columns.scopeScale')}</th>
                  <th className="label px-4 py-3.5">{t('history.table.columns.auditStatus')}</th>
                  <th className="label px-4 py-3.5">{t('history.table.columns.timestamp')}</th>
                  <th className="label px-4 py-3.5 text-right">{t('history.table.columns.actions')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRecords.map(record => {
                  const score = record.green_score ?? 0;
                  const isPass = score >= threshold;
                  const isRescanning = rescanningId === record.id;

                  return (
                       <tr key={record.id} className="hover:bg-slate-50/80 dark:hover:bg-slate-800/50 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-olive-50 dark:bg-olive-900/20 border border-olive-200 dark:border-olive-800 flex items-center justify-center shrink-0 text-olive-800 dark:text-olive-300 mt-0.5">
                            <GitBranch size={13} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-slate-900 dark:text-slate-100 text-sm truncate max-w-xs">
                                {record.full_name || record.name}
                              </span>
                              {record.html_url && (
                                <a
                                  href={record.html_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-1.5 py-0.5 rounded hover:bg-slate-200 dark:hover:bg-slate-600 transition-colors"
                                >
                                  GitHub
                                  <ExternalLink size={9} className="opacity-70" />
                                </a>
                              )}
                            </div>
                            {record.default_branch && (
                              <p className="text-xs text-slate-500 dark:text-slate-400 font-mono truncate max-w-sm mt-0.5">
                                @{record.default_branch}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <div className="flex items-center gap-2.5">
                          <ScoreBadge score={score} size="sm" />
                          <div>
                            <span
                              className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase tracking-wider ${
                                isPass
                                  ? 'bg-olive-50 dark:bg-olive-900/30 text-olive-900 dark:text-olive-200 border border-olive-200 dark:border-olive-800'
                                  : 'bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-200 border dark:border-red-800'
                              }`}
                            >
                              {isPass ? t('history.status.verified') : t('history.status.actionRequired')}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-700 dark:text-slate-300 font-medium">
                        {record.total_files} <span className="text-slate-400 dark:text-slate-500 font-normal">{t('history.table.files')}</span>
                        <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono">
                          {record.total_lines?.toLocaleString() || 0} LOC
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300">
                          {isPass ? t('history.table.status.verified') : t('history.table.status.blocked')}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-500 dark:text-slate-400 whitespace-nowrap">
                        <span className="flex items-center gap-1.5 font-mono">
                          <Calendar size={12} className="text-slate-400 dark:text-slate-500" />
                          {record.created_at ? new Date(record.created_at).toLocaleDateString() : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            onClick={() => handleViewRecord(record)}
                            variant="ghost"
                            size="sm"
                            className="text-xs text-slate-700 dark:text-slate-300"
                            title={t('history.inspectButton')}
                          >
                            <Eye size={12} />
                            {t('history.inspectButton')}
                          </Button>
                          <Button
                            onClick={() => handleRescan(record)}
                            disabled={isRescanning}
                            variant="secondary"
                            size="sm"
                            className="text-xs text-olive-900 dark:text-olive-200 border border-olive-300 dark:border-olive-700"
                          >
                            <RotateCw size={12} className={isRescanning ? 'animate-spin text-olive-800' : ''} />
                            {isRescanning ? t('history.rescanning') : t('history.rescanButton')}
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
