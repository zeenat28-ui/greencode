import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, githubService, gridService } from '../services/greencodeApi';
import { GitHubRepo, ScanResult, TaskStatus, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import {
  Search, Loader2, AlertCircle, RefreshCw, GitBranch, Star,
  Lock, Globe, ChevronDown, CheckCircle2, Cpu, ArrowRight,
} from 'lucide-react';

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

function formatSize(kb: number): string {
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${kb} KB`;
}

export default function ScanRepository() {
  const navigate = useNavigate();
  const [, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');

  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(true);
  const [reposError, setReposError] = useState<string | null>(null);

  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<GitHubRepo | null>(null);
  const [ref, setRef] = useState<string>('');
  const [branches, setBranches] = useState<string[]>([]);
  const [branchesLoading, setBranchesLoading] = useState(false);

  const [isScanning, setIsScanning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [scanError, setScanError] = useState<string | null>(null);
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const pollTimer = useRef<number | null>(null);

  const loadRepos = useCallback(async () => {
    setReposLoading(true);
    setReposError(null);
    try {
      const res = await githubService.listRepositories(50);
      const list = res.data.repositories || [];
      setRepos(list);
      if (res.data.message && list.length === 0) setReposError(res.data.message);
    } catch (err: any) {
      setRepos([]);
      setReposError(err?.response?.data?.detail || 'Could not load your repositories from GitHub.');
    } finally {
      setReposLoading(false);
    }
  }, []);

  useEffect(() => { loadRepos(); }, [loadRepos]);

  useEffect(() => {
    gridService.getZoneIntensity(activeZone).then((r) => setGridData(r.data)).catch(() => setGridData(null));
  }, [activeZone]);

  useEffect(() => () => {
    if (pollTimer.current) window.clearTimeout(pollTimer.current);
  }, []);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return repos;
    return repos.filter(
      (r) =>
        r.full_name.toLowerCase().includes(q) ||
        r.name.toLowerCase().includes(q) ||
        (r.description || '').toLowerCase().includes(q)
    );
  }, [repos, query]);

  const selectRepo = async (repo: GitHubRepo) => {
    setSelected(repo);
    setRef(repo.default_branch || 'main');
    setBranches([]);
    setScanError(null);
    setBranchesLoading(true);
    try {
      const res = await githubService.listBranches(repo.owner || repo.full_name.split('/')[0], repo.name);
      setBranches(res.data.branches.map((b) => b.name));
    } catch {
      setBranches([]);
    } finally {
      setBranchesLoading(false);
    }
  };

  const applyEnergyEstimates = (result: ScanResult): ScanResult => {
    if (typeof result.energy_wh === 'number' && result.energy_wh > 0) return result;
    const violations = result.total_violations || 0;
    const lines = result.total_lines || 0;
    const cpuPct = violations > 0 ? 45 : 18;
    const memMb = Math.max(64, lines * 0.8);
    const duration = Math.max(0.5, lines * 0.015);
    const pIdle = 15;
    const pPeak = 120;
    const pMem = 0.3725;
    const pue = 1.2;
    const watts = (pIdle + ((pPeak - pIdle) * cpuPct) / 100 + (memMb / 1024) * pMem) * pue;
    const energyWh = (watts * duration) / 3600;
    const intensity = gridData?.carbon_intensity || 215;
    return { ...result, energy_wh: energyWh, carbon_g: (energyWh / 1000) * intensity };
  };

  const pollTask = (taskId: string) =>
    new Promise<ScanResult>((resolve, reject) => {
      const startedAt = Date.now();
      const tick = async () => {
        if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          reject(new Error('The audit is taking longer than expected. Check the History page shortly.'));
          return;
        }
        try {
          const res = await scanService.getTaskStatus(taskId);
          const task: TaskStatus = res.data;
          if (task.progress_message) setStatusMessage(task.progress_message);
          if (task.status === 'Completed' && task.result) { resolve(task.result); return; }
          if (task.status === 'Failed') {
            reject(new Error(task.error || 'The audit failed.'));
            return;
          }
          setStatusMessage(task.progress_message || 'Auditing source tree...');
          pollTimer.current = window.setTimeout(tick, POLL_INTERVAL_MS);
        } catch (err: any) {
          reject(err?.response?.data?.detail || 'Lost contact with the audit worker.');
        }
      };
      tick();
    });

  const handleScan = async () => {
    if (!selected) return;
    setIsScanning(true);
    setScanError(null);
    setStatusMessage('Starting audit...');

    try {
      let result: ScanResult;
      try {
        const res = await scanService.scanGitHub(selected.full_name, ref || undefined);
        result = res.data;
        setStatusMessage('Audit complete.');
      } catch (err: any) {
        const status = err?.response?.status;
        if (status !== 413) throw err;
        setStatusMessage('Repository is large - running in the background...');
        const queued = await scanService.scanGitHubAsync(selected.full_name, ref || undefined);
        result = await pollTask(queued.data.task_id);
      }

      setScanData(applyEnergyEstimates(result));
      navigate('/dashboard');
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || err?.message || 'The audit could not be completed.');
      setStatusMessage('');
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Audit a Repository</h1>
        <p className="text-sm text-slate-500 mt-1">
          Pick a repository from your connected GitHub account. We clone it server-side,
          analyse every source file, and score its carbon efficiency.
        </p>
      </div>

      {scanError && (
        <div role="alert" className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200">
          <AlertCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <p className="text-sm text-red-700 leading-relaxed flex-1">{scanError}</p>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 card p-5">
          <div className="flex items-center justify-between gap-3 mb-4">
            <h2 className="text-sm font-bold text-slate-900">Your Repositories</h2>
            <button onClick={loadRepos} disabled={reposLoading} className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5">
              <RefreshCw size={12} className={reposLoading ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>

          <div className="relative mb-4">
            <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter by name or description..." className="input pl-9 text-sm" />
          </div>

          {reposLoading ? (
            <div className="flex flex-col items-center justify-center py-14 text-slate-400">
              <Loader2 size={24} className="animate-spin text-emerald-600 mb-3" />
              <p className="text-sm">Loading repositories from GitHub...</p>
            </div>
          ) : reposError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle size={24} className="text-red-400 mb-3" />
              <p className="text-sm text-slate-600 max-w-sm">{reposError}</p>
              <button onClick={loadRepos} className="btn-secondary text-xs mt-4 px-3 py-1.5">Try again</button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <GitBranch size={24} className="text-slate-300 mb-3" />
              <p className="text-sm text-slate-500">
                {repos.length === 0 ? 'No repositories are visible to this token.' : 'No repositories match that filter.'}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 -mx-1 max-h-[26rem] overflow-y-auto">
              {filtered.map((repo) => {
                const isSelected = selected?.full_name === repo.full_name;
                return (
                  <li key={repo.full_name}>
                    <button onClick={() => selectRepo(repo)} className={`w-full text-left px-3 py-3 rounded-lg transition-colors ${isSelected ? 'bg-emerald-50 ring-1 ring-emerald-200' : 'hover:bg-slate-50'}`}>
                      <div className="flex items-start gap-3">
                        <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${isSelected ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-500'}`}>
                          <GitBranch size={16} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-sm font-bold text-slate-900 truncate">{repo.full_name}</span>
                            {repo.private ? <Lock size={11} className="text-amber-500 shrink-0" /> : <Globe size={11} className="text-slate-300 shrink-0" />}
                            {repo.archived && <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-100 text-slate-500">ARCHIVED</span>}
                          </div>
                          {repo.description && <p className="text-xs text-slate-500 truncate mt-0.5">{repo.description}</p>}
                          <div className="flex items-center gap-3 mt-1.5 text-[11px] text-slate-400 font-medium">
                            <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-600">{repo.language}</span>
                            <span className="flex items-center gap-1"><GitBranch size={10} /> {repo.default_branch}</span>
                            <span>{formatSize(repo.size_kb)}</span>
                            {repo.stars > 0 && <span className="flex items-center gap-1"><Star size={10} /> {repo.stars}</span>}
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 size={18} className="text-emerald-600 shrink-0 mt-1" />}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </div>

        <div className="space-y-5">
          <div className="card p-5">
            <h2 className="text-sm font-bold text-slate-900 mb-4">Scan Configuration</h2>
            {selected ? (
              <div className="space-y-4">
                <div>
                  <p className="label mb-1">Repository</p>
                  <p className="text-sm font-bold text-slate-900 truncate">{selected.full_name}</p>
                </div>
                <div>
                  <label className="label mb-1.5" htmlFor="ref-select">Branch / Ref</label>
                  <div className="relative">
                    <select id="ref-select" value={ref} onChange={(e) => setRef(e.target.value)} className="input appearance-none pr-9 text-sm">
                      {branches.length === 0 && <option value={ref}>{ref || selected.default_branch}</option>}
                      {branches.map((b) => <option key={b} value={b}>{b}</option>)}
                    </select>
                    <ChevronDown size={15} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                  </div>
                  {branchesLoading && <p className="text-[11px] text-slate-400 mt-1 flex items-center gap-1"><Loader2 size={10} className="animate-spin" /> Loading branches...</p>}
                </div>
                <button onClick={handleScan} disabled={isScanning} className="btn-primary w-full flex items-center justify-center gap-2">
                  {isScanning ? (<><Loader2 size={15} className="animate-spin" /> Auditing...</>) : (<><ArrowRight size={15} /> Run Green Score Audit</>)}
                </button>
              </div>
            ) : (
              <div className="text-center py-8">
                <Cpu size={22} className="text-slate-300 mx-auto mb-2.5" />
                <p className="text-sm text-slate-500">Select a repository to continue</p>
              </div>
            )}
          </div>

          {isScanning && (
            <div className="card p-4 border-emerald-200 bg-emerald-50/40">
              <div className="flex items-start gap-3">
                <Loader2 size={16} className="animate-spin text-emerald-600 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-800">Audit in progress</p>
                  <p className="text-xs text-slate-600 mt-0.5 break-words">{statusMessage || 'Cloning repository and parsing syntax trees...'}</p>
                </div>
              </div>
            </div>
          )}

          <div className="card p-5">
            <h3 className="text-xs font-bold text-slate-900 mb-3">What gets analysed</h3>
            <ul className="space-y-2 text-xs text-slate-600">
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-slate-400 shrink-0 mt-0.5" /> Every source file in the tree, across 500+ languages</li>
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-slate-400 shrink-0 mt-0.5" /> Nested loops, un-cached network calls, leaked DB cursors, quadratic string building</li>
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-slate-400 shrink-0 mt-0.5" /> Grid carbon intensity from {activeZone}{gridData ? ` (${gridData.marginal_carbon_intensity ?? gridData.carbon_intensity} g/kWh)` : ''}</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
