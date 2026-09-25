import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { scanService } from '../services/greencodeApi';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { RepositoryRecord, RepositoryPage, ScanResult } from '../types';
import ScoreBadge from '../components/common/ScoreBadge';
import {
  Calendar, ExternalLink, RefreshCw, GitBranch, Search,
  Eye, RotateCw, Leaf, Zap, AlertTriangle, FolderGit2,
} from 'lucide-react';

export default function History() {
  const navigate = useNavigate();
  const [historyData, setHistoryData] = useLocalStorage<RepositoryPage | null>('greencode_history', null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
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
    try {
      const resp = await scanService.getHistory();
      setHistoryData(resp.data);
    } catch {
      // keep existing cached history if any
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  /**
   * Re-run a stored audit. In GitHub-only mode every record is a GitHub
   * repository, so there is no local-path branch to worry about.
   */
  const handleRescan = async (record: RepositoryRecord) => {
    const slug = record.full_name || record.path_or_url;
    if (!slug) {
      setRescanError('This record has no repository reference.');
      return;
    }
    setRescanningId(record.id);
    setRescanError(null);
    try {
      const resp = await scanService.scanGitHub(slug, record.default_branch || undefined);
      setScanData(resp.data);
      await loadHistory(true);
      navigate('/dashboard');
    } catch (err: any) {
      setRescanError(
        err?.response?.data?.detail || `Could not re-audit ${slug}. Verify the repository still exists and is accessible.`
      );
    } finally {
      setRescanningId(null);
    }
  };

  /** Load a stored audit into the active session (score + provenance only). */
  const handleViewRecord = (record: RepositoryRecord) => {
    const loadedScan: ScanResult = {
      repo_path: record.full_name || record.path_or_url || record.name,
      repo_id: record.id,
      full_name: record.full_name || undefined,
      default_branch: record.default_branch || undefined,
      html_url: record.html_url || undefined,
      source: 'github',
      is_github: true,
      total_files: record.total_files || 0,
      total_lines: record.total_lines || 0,
      green_score: record.green_score || 0,
      total_violations: 0,
      violation_breakdown: {},
      languages_breakdown: {},
      violations: [],
      file_results: [],
    };

    setScanData(loadedScan);
    navigate('/dashboard');
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
      <div className="flex flex-col items-center justify-center py-28 text-slate-500">
        <RefreshCw size={28} className="animate-spin text-emerald-600 mb-3" />
        <p className="text-sm font-medium">Loading repository audit archives...</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Audit History</h1>
          <p className="text-sm text-slate-500 mt-1">
            Historical Green Scores, anti-pattern trends, and compliance records across repositories
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* Bug Fix #5: Distinct refreshing state with proper disabled attribute and spinning icon */}
          <button
            onClick={() => loadHistory(true)}
            disabled={refreshing || loading}
            className="btn-secondary flex items-center gap-2 text-xs font-semibold px-3 py-2 disabled:opacity-50"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin text-emerald-600' : ''} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </button>
          <Link to="/scan" className="btn-primary flex items-center gap-1.5 text-xs font-semibold px-3.5 py-2">
            <GitBranch size={13} />
            New Audit
          </Link>
        </div>
      </div>

      {/* Rescan Error Notice */}
      {rescanError && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-800 text-sm">
          <AlertTriangle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold">Rescan encountered an issue</p>
            <p className="text-xs text-red-600 mt-0.5">{rescanError}</p>
          </div>
          <button
            onClick={() => setRescanError(null)}
            className="text-xs text-red-600 hover:text-red-800 underline font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <p className="label mb-1">Repositories Audited</p>
          <p className="text-2xl font-black text-slate-900">{records.length}</p>
          <p className="text-xs text-slate-500 mt-1">Archived scans</p>
        </div>
        <div className="card p-4">
          <p className="label mb-1">Fleet Average Score</p>
          <div className="flex items-center gap-2">
            <p className="text-2xl font-black text-emerald-600">{records.length ? avgScore : '—'}</p>
            {records.length > 0 && (
              <span
                className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                  avgScore >= threshold ? 'bg-emerald-100 text-emerald-800' : 'bg-red-100 text-red-800'
                }`}
              >
                {avgScore >= threshold ? 'Pass' : 'Under Target'}
              </span>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">Target threshold: ≥ {threshold}</p>
        </div>
        <div className="card p-4">
          <p className="label mb-1">Total Carbon Saved</p>
          <p className="text-2xl font-black text-emerald-600 flex items-center gap-1.5">
            <Leaf size={20} className="text-emerald-500" />
            {cumulative?.total_carbon_saved_gco2_10k_runs != null
              ? `${cumulative.total_carbon_saved_gco2_10k_runs.toFixed(1)} g`
              : '0.0 g'}
          </p>
          <p className="text-xs text-slate-500 mt-1">Per 10,000 runs</p>
        </div>
        <div className="card p-4">
          <p className="label mb-1">Synthesized Fixes</p>
          <p className="text-2xl font-black text-blue-600 flex items-center gap-1.5">
            <Zap size={20} className="text-blue-500" />
            {cumulative?.total_refactoring_operations ?? 0}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            {cumulative?.average_energy_reduction_pct != null
              ? `${cumulative.average_energy_reduction_pct.toFixed(0)}% avg energy cut`
              : 'Applied optimizations'}
          </p>
        </div>
      </div>

      {records.length === 0 ? (
        <div className="card p-14 text-center">
          <div className="w-14 h-14 rounded-2xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto mb-4 text-emerald-600 shadow-sm">
            <FolderGit2 size={26} />
          </div>
          <h3 className="font-bold text-slate-800 text-base mb-1">No repositories audited yet</h3>
          <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
            Repositories and archives you scan will be recorded here with complete audit reports, violation counts, and Green Scores.
          </p>
          <Link to="/scan" className="btn-primary inline-flex items-center gap-2">
            <GitBranch size={15} /> Run First Audit
          </Link>
        </div>
      ) : (
        <div className="card overflow-hidden">
          {/* Table Toolbar */}
          <div className="p-4 border-b border-slate-200/80 bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="relative w-full sm:w-72">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input
                type="text"
                placeholder="Filter by repository name or path..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="input pl-9 py-1.5 text-xs w-full bg-white"
              />
            </div>
            <span className="text-xs text-slate-500">
              Showing <strong>{filteredRecords.length}</strong> of {records.length} repositories
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 border-b border-slate-200/80 text-slate-500">
                <tr>
                  <th className="label px-4 py-3.5">Repository / Path</th>
                  <th className="label px-4 py-3.5">Green Score</th>
                  <th className="label px-4 py-3.5">Files</th>
                  <th className="label px-4 py-3.5">Issues</th>
                  <th className="label px-4 py-3.5">Audited</th>
                  <th className="label px-4 py-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredRecords.map(record => {
                  const score = record.green_score ?? 0;
                  const isPass = score >= threshold;
                  const isRescanning = rescanningId === record.id;

                  return (
                    <tr key={record.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-3.5">
                        <div className="flex items-start gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-slate-100 flex items-center justify-center shrink-0 text-slate-700 mt-0.5">
                            <GitBranch size={14} />
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-1.5">
                              <span className="font-bold text-slate-900 text-sm truncate max-w-xs">
                                {record.full_name || record.name}
                              </span>
                              {record.html_url && (
                                <a
                                  href={record.html_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="inline-flex items-center gap-0.5 text-[10px] font-semibold bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded hover:bg-slate-200 transition-colors"
                                >
                                  GitHub
                                  <ExternalLink size={9} className="opacity-70" />
                                </a>
                              )}
                            </div>
                            {record.default_branch && (
                              <p className="text-xs text-slate-400 font-mono truncate max-w-sm mt-0.5">
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
                              className={`text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider ${
                                isPass
                                  ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                                  : 'bg-red-50 text-red-700 border border-red-200'
                              }`}
                            >
                              {isPass ? 'Passed' : 'Blocked'}
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-600 font-medium">
                        {record.total_files} <span className="text-slate-400 font-normal">files</span>
                        <div className="text-[11px] text-slate-400 font-mono">
                          {record.total_lines?.toLocaleString() || 0} LOC
                        </div>
                      </td>
                      <td className="px-4 py-3.5">
                        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-slate-100 text-slate-600">
                          View score
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-xs text-slate-500 whitespace-nowrap">
                        <span className="flex items-center gap-1.5">
                          <Calendar size={12} className="text-slate-400" />
                          {record.created_at ? new Date(record.created_at).toLocaleDateString() : '—'}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleViewRecord(record)}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-slate-600 hover:text-slate-900 bg-slate-100 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg transition-colors"
                            title="Load this audit into Dashboard"
                          >
                            <Eye size={12} />
                            View
                          </button>
                          <button
                            onClick={() => handleRescan(record)}
                            disabled={isRescanning}
                            className="inline-flex items-center gap-1 text-xs font-semibold text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 px-2.5 py-1.5 rounded-lg transition-colors disabled:opacity-50"
                          >
                            <RotateCw size={12} className={isRescanning ? 'animate-spin' : ''} />
                            {isRescanning ? 'Scanning...' : 'Rescan'}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}

