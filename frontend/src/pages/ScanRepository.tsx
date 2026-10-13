import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, githubService, gridService } from '../services/greencodeApi';
import { GitHubRepo, ScanResult, TaskStatus, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import {
  Search, Loader2, AlertCircle, RefreshCw, GitBranch, Star,
  Lock, Globe, ChevronDown, CheckCircle2, Cpu, ArrowRight,
  Play, FileCode2
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

  const [directSlug, setDirectSlug] = useState('');
  const [localSubpath, setLocalSubpath] = useState('app');

  const handleScanLocalSubpath = async (subpath: string, repoLabel: string) => {
    setIsScanning(true);
    setScanError(null);
    setStatusMessage(`Auditing local workspace path '${subpath}'...`);
    try {
      const res = await fetch('/api/scan/local-workspace', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subpath,
          repo_name: repoLabel,
          team_id: 'core-platform',
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(body?.detail || 'Local workspace audit failed.');
      }
      setScanData(applyEnergyEstimates(body));
      navigate('/dashboard');
    } catch (err: any) {
      setScanError(err?.message || 'Could not complete workspace audit.');
    } finally {
      setIsScanning(false);
    }
  };

  const handleDirectGitHubScan = async () => {
    const clean = directSlug
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();
    if (!clean.includes('/')) {
      setScanError('Enter a valid GitHub repository slug (e.g. zeenat28-ui/greencode) or URL.');
      return;
    }
    setIsScanning(true);
    setScanError(null);
    setStatusMessage(`Auditing GitHub repository '${clean}'...`);
    try {
      const res = await scanService.scanGitHub(clean);
      setScanData(applyEnergyEstimates(res.data));
      navigate('/dashboard');
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || err?.message || 'Could not audit GitHub repository.');
    } finally {
      setIsScanning(false);
    }
  };

  const LIVE_WORKSPACE_TARGETS = [
    {
      subpath: 'app',
      repo_name: 'greencode-org/greencode-backend',
      name: 'app/ (GreenCode Core Engine)',
      language: 'Python',
      description: 'Live self-audit of GreenCode FastAPI routers, AST/Tree-sitter parser, and calibrated energy profiler.',
    },
    {
      subpath: 'frontend/src',
      repo_name: 'greencode-org/greencode-frontend',
      name: 'frontend/src/ (React + TypeScript UI)',
      language: 'TypeScript',
      description: 'Live lexical & CST static analysis of all React pages, hooks, and API client services.',
    },
  ];

  return (
    <div className="space-y-5">
      <div className="border-b border-zinc-200/80 pb-3">
        <div className="flex items-center gap-2">
           <h1 className="text-lg font-semibold text-zinc-950 tracking-tight">Repository Scanner</h1>
           <Badge variant="olive">Polyglot AST &amp; Call-Graph</Badge>
         </div>
        <p className="text-xs text-zinc-500 mt-0.5">
          Audit a public GitHub repository, connected organization repo, or local workspace directory.
        </p>
      </div>

      {scanError && (
        <div role="alert" className="flex items-start gap-3 p-3.5 rounded-lg bg-rose-50 border border-rose-200">
          <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
          <p className="text-xs text-rose-700 leading-relaxed flex-1">{scanError}</p>
        </div>
      )}

      {/* Direct Public GitHub URL / Local Path Scanner */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card padding="lg" className="space-y-2.5">
          <label className="block text-xs font-semibold text-zinc-800">
            Public GitHub Repository (URL or owner/repo)
          </label>
          <div className="flex gap-2">
            <Input
              type="text"
              value={directSlug}
              onChange={(e) => setDirectSlug(e.target.value)}
              placeholder="e.g. zeenat28-ui/greencode"
              className="text-xs font-mono flex-1"
            />
            <Button
              onClick={handleDirectGitHubScan}
              disabled={isScanning || !directSlug.trim()}
              variant="primary"
              size="sm"
              className="text-xs px-3.5 py-2"
            >
              <Play size={11} /> Scan GitHub
            </Button>
          </div>
        </Card>

        <Card padding="lg" className="space-y-2.5">
          <label className="block text-xs font-semibold text-zinc-800">
            Local Workspace Subdirectory
          </label>
          <div className="flex gap-2">
            <Input
              type="text"
              value={localSubpath}
              onChange={(e) => setLocalSubpath(e.target.value)}
              placeholder="e.g. app, frontend/src, scripts"
              className="text-xs font-mono flex-1"
            />
            <Button
              onClick={() => handleScanLocalSubpath(localSubpath.trim() || '.', `greencode-org/${(localSubpath.trim() || 'workspace').replace(/[^a-zA-Z0-9_-]/g, '-')}`)}
              disabled={isScanning}
              variant="primary"
              size="sm"
              className="text-xs px-3.5 py-2"
            >
              <Play size={11} /> Scan Path
            </Button>
          </div>
        </Card>
      </div>

      {/* Reference Workspace Targets */}
      <Card padding="lg">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3 pb-2.5 border-b border-zinc-100">
          <div>
            <h2 className="section-title">Reference Workspace Targets</h2>
            <p className="text-[11px] text-zinc-500 mt-0.5">
              Execute multi-language AST and call-graph static analysis against on-disk targets.
            </p>
          </div>
          <Badge variant="olive" className="w-fit">
            AST + Call-Graph Engine
          </Badge>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
          {LIVE_WORKSPACE_TARGETS.map((target) => (
            <div
              key={target.subpath}
              className="p-3.5 rounded-lg border border-slate-200 bg-white hover:border-olive-400 hover:shadow-sm transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-1.5 min-w-0">
                    <FileCode2 size={14} className="text-olive-700 shrink-0" />
                    <span className="font-mono text-xs font-bold text-slate-900 truncate">
                      {target.name}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">
                    {target.language}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-1 line-clamp-2">
                  {target.description}
                </p>
              </div>

                <div className="mt-3 pt-2.5 border-t border-slate-100 flex items-center justify-between">
                <span className="text-[10px] font-mono text-slate-400">
                  path: {target.subpath}
                </span>
                <Button
                  onClick={() => handleScanLocalSubpath(target.subpath, target.repo_name)}
                  disabled={isScanning}
                  variant="primary"
                  size="sm"
                  className="text-xs px-2.5 py-1"
                >
                  <Play size={10} />
                  Run Live Audit
                </Button>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <Card padding="lg" className="lg:col-span-2">
          <div className="flex items-center justify-between gap-3 mb-3 pb-2 border-b border-slate-100">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">Your GitHub Repositories</h2>
            <Button onClick={loadRepos} disabled={reposLoading} variant="secondary" size="sm" className="text-xs px-2.5 py-1">
              <RefreshCw size={11} className={reposLoading ? 'animate-spin' : ''} />
              Refresh
            </Button>
          </div>

          <div className="relative mb-3">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <Input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search by repository name..." className="pl-9 text-xs py-2 bg-white" />
          </div>

          {reposLoading ? (
            <div className="flex flex-col items-center justify-center py-14 text-slate-400">
              <Loader2 size={22} className="animate-spin text-olive-700 mb-2.5" />
              <p className="text-xs">Loading repositories from GitHub...</p>
            </div>
          ) : reposError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle size={22} className="text-rose-500 mb-2" />
              <p className="text-xs text-slate-600 max-w-sm">{reposError}</p>
              <Button onClick={loadRepos} variant="secondary" size="sm" className="text-xs mt-3 px-3 py-1.5">Retry Sync</Button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <GitBranch size={22} className="text-slate-300 mb-2" />
              <p className="text-xs text-slate-500 font-mono">
                {repos.length === 0 ? 'No repositories found under this token scope.' : 'No repositories match active query filter.'}
              </p>
            </div>
          ) : (
            <ul className="divide-y divide-slate-100 -mx-1 max-h-[26rem] overflow-y-auto">
              {filtered.map((repo) => {
                const isSelected = selected?.full_name === repo.full_name;
                return (
                  <li key={repo.full_name}>
                    <button onClick={() => selectRepo(repo)} className={`w-full text-left px-3 py-2.5 rounded-lg transition-colors ${isSelected ? 'bg-olive-50 ring-1 ring-olive-600' : 'hover:bg-slate-50'}`}>
                      <div className="flex items-start gap-3">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${isSelected ? 'bg-olive-900 text-olive-100' : 'bg-slate-100 text-slate-500'}`}>
                          <GitBranch size={15} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="text-xs font-bold text-slate-900 font-mono truncate">{repo.full_name}</span>
                            {repo.private ? <Lock size={10} className="text-amber-500 shrink-0" /> : <Globe size={10} className="text-slate-300 shrink-0" />}
                            {repo.archived && <Badge variant="default" className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-slate-100 text-slate-500 font-mono">ARCHIVED</Badge>}
                          </div>
                          {repo.description && <p className="text-[11px] text-slate-500 truncate mt-0.5">{repo.description}</p>}
                          <div className="flex items-center gap-2.5 mt-1 text-[10px] text-slate-400 font-mono">
                            <span className="px-1.5 py-0.2 rounded bg-slate-100 text-slate-600">{repo.language}</span>
                            <span className="flex items-center gap-1"><GitBranch size={9} /> {repo.default_branch}</span>
                            <span>{formatSize(repo.size_kb)}</span>
                            {repo.stars > 0 && <span className="flex items-center gap-1"><Star size={9} /> {repo.stars}</span>}
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 size={16} className="text-olive-700 shrink-0 mt-1" />}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <div className="space-y-4">
          <Card padding="lg">
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-3 pb-2 border-b border-slate-100">
              Audit Configuration
            </h2>
            {selected ? (
              <div className="space-y-3.5">
                <div>
                  <p className="label mb-0.5">Selected Repository</p>
                  <p className="text-xs font-bold text-slate-900 font-mono truncate">{selected.full_name}</p>
                </div>
                <div>
                  <label className="label mb-1 block" htmlFor="ref-select">Target Branch</label>
                  <div className="relative">
                    <Select id="ref-select" value={ref} onChange={(e) => setRef(e.target.value)} className="appearance-none pr-8 text-xs font-mono py-1.5 bg-white">
                      {branches.length === 0 && <option value={ref}>{ref || selected.default_branch}</option>}
                      {branches.map((b) => <option key={b} value={b}>{b}</option>)}
                    </Select>
                    <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                  </div>
                  {branchesLoading && <p className="text-[10px] font-mono text-slate-400 mt-1 flex items-center gap-1"><Loader2 size={10} className="animate-spin" /> Fetching branches...</p>}
                </div>
                <Button onClick={handleScan} disabled={isScanning} variant="primary" className="w-full flex items-center justify-center gap-2 py-2.5 shadow-sm">
                  {isScanning ? (<><Loader2 size={14} className="animate-spin text-white" /> Auditing Code...</>) : (<><ArrowRight size={14} /> Start Code Audit</>)}
                </Button>
              </div>
            ) : (
              <div className="text-center py-8">
                <Cpu size={20} className="text-slate-300 mx-auto mb-2" />
                <p className="text-xs text-slate-500">Select a repository from the list to audit</p>
              </div>
            )}
          </Card>

          {isScanning && (
            <Card padding="sm" className="border-olive-300 bg-olive-50/70">
              <div className="flex items-start gap-3">
                <Loader2 size={15} className="animate-spin text-olive-700 shrink-0 mt-0.5" />
                <div className="min-w-0">
                  <p className="text-xs font-bold text-slate-900">Audit in Progress</p>
                  <p className="text-[11px] text-slate-600 mt-0.5 break-words">{statusMessage || 'Analyzing source files and checking energy patterns...'}</p>
                </div>
              </div>
            </Card>
          )}

          <Card padding="lg">
            <h3 className="text-xs font-bold text-slate-900 mb-2">What GreenCode Checks:</h3>
            <ul className="space-y-2 text-xs text-slate-600">
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-olive-700 shrink-0 mt-0.5" /> High-complexity nested loops and recursive calls</li>
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-olive-700 shrink-0 mt-0.5" /> Unindexed database queries and memory leaks</li>
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-olive-700 shrink-0 mt-0.5" /> Heavy uncompressed payloads and blocking network I/O</li>
              <li className="flex gap-2"><CheckCircle2 size={13} className="text-olive-700 shrink-0 mt-0.5" /> Carbon emissions calculated for active grid: {activeZone}</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
