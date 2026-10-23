import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, githubService } from '../services/greencodeApi';
import { GitHubRepo, ScanResult, TaskStatus } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import {
  Search, Loader2, AlertCircle, RefreshCw, GitBranch, Star,
  Lock, Globe, ChevronDown, CheckCircle2, Cpu, ArrowRight, Link2,
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';

const POLL_INTERVAL_MS = 1500;
const POLL_TIMEOUT_MS = 10 * 60 * 1000;

function formatSize(kb: number): string {
  if (kb >= 1024) return `${(kb / 1024).toFixed(1)} MB`;
  return `${kb} KB`;
}

export default function ScanRepository() {
  const t = useT();
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
  const [branchesError, setBranchesError] = useState<string | null>(null);

  const [isScanning, setIsScanning] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string>('');
  const [scanError, setScanError] = useState<string | null>(null);
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [pairingError, setPairingError] = useState<string | null>(null);
  const [isPairing, setIsPairing] = useState(false);
  const pollTimer = useRef<number | null>(null);
  const branchRequestVersion = useRef(0);

  const loadRepos = useCallback(async () => {
    setReposLoading(true);
    setReposError(null);
    try {
      const res = await githubService.listRepositories(100);
      const list = res.data.repositories || [];
      setRepos(list);
      if (res.data.message && list.length === 0) setReposError(res.data.message);
    } catch (err: any) {
      setRepos([]);
      setReposError(err?.response?.data?.detail || t('scan.couldNotLoadRepos'));
    } finally {
      setReposLoading(false);
    }
  }, []);

  useEffect(() => { loadRepos(); }, [loadRepos]);

  useEffect(() => () => {
    branchRequestVersion.current += 1;
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
    const requestVersion = ++branchRequestVersion.current;
    setSelected(repo);
    setRef(repo.default_branch || 'main');
    setBranches([]);
    setBranchesError(null);
    setScanError(null);
    setPairingCode(null);
    setPairingError(null);
    try {
      await githubService.saveAlexaRepository(repo.full_name);
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || 'Could not save the selected repository for Alexa.');
    }
    setBranchesLoading(true);
    try {
      const res = await githubService.listBranches(repo.owner || repo.full_name.split('/')[0], repo.name);
      if (requestVersion !== branchRequestVersion.current) return;
      setBranches(res.data.branches.map((b) => b.name));
    } catch (err: any) {
      if (requestVersion !== branchRequestVersion.current) return;
      setBranches([]);
      setBranchesError(err?.response?.data?.detail || t('scan.branchLoadError'));
    } finally {
      if (requestVersion === branchRequestVersion.current) setBranchesLoading(false);
    }
  };

  const handlePairAlexa = async () => {
    if (!selected) return;
    setIsPairing(true);
    setPairingCode(null);
    setPairingError(null);
    try {
      const response = await githubService.createAlexaPairingCode(selected.full_name);
      setPairingCode(response.data.code);
    } catch (err: any) {
      setPairingError(err?.response?.data?.detail || 'Could not create an Alexa pairing code.');
    } finally {
      setIsPairing(false);
    }
  };

  const pollTask = (taskId: string) =>
    new Promise<ScanResult>((resolve, reject) => {
      const startedAt = Date.now();
      const tick = async () => {
        if (Date.now() - startedAt > POLL_TIMEOUT_MS) {
          reject(new Error(t('scan.takingLonger')));
          return;
        }
        try {
          const res = await scanService.getTaskStatus(taskId);
          const task: TaskStatus = res.data;
          if (task.progress_message) setStatusMessage(task.progress_message);
          if (task.status === 'Completed' && task.result) { resolve(task.result); return; }
          if (task.status === 'Failed') {
            reject(new Error(task.error || t('scan.failed')));
            return;
          }
          setStatusMessage(task.progress_message || 'Auditing source tree...');
          pollTimer.current = window.setTimeout(tick, POLL_INTERVAL_MS);
        } catch (err: any) {
           reject(new Error(err?.response?.data?.detail || t('scan.lostContact')));
        }
      };
      tick();
    });

  const handleScan = async () => {
    if (!selected) return;
    setIsScanning(true);
    setScanError(null);
    setStatusMessage(t('scan.starting'));

    try {
      let result: ScanResult;
      try {
        const res = await scanService.scanGitHub(selected.full_name, ref || undefined);
        result = res.data;
        setStatusMessage(t('scan.auditComplete'));
      } catch (err: any) {
        const status = err?.response?.status;
        if (status !== 413) throw err;
        setStatusMessage(t('scan.largeRepo'));
        const queued = await scanService.scanGitHubAsync(selected.full_name, ref || undefined);
        result = await pollTask(queued.data.task_id);
      }

      setScanData(result);
      navigate('/issues');
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || err?.message || t('scan.couldNotComplete'));
      setStatusMessage('');
    } finally {
      setIsScanning(false);
    }
  };

  return (
    <div className="mx-auto max-w-[1440px] space-y-5 pb-2">
      <header className="border-b border-[var(--gc-border-default)] pb-4">
        <p className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-emerald-700 dark:text-emerald-300">
          {t('scan.githubAudit')}
        </p>
        <div className="flex flex-wrap items-center gap-2.5">
          <h1 className="text-2xl font-semibold tracking-tight text-[var(--gc-text-primary)]">{t('scan.title')}</h1>
          <Badge variant="olive">Polyglot AST &amp; Call-Graph</Badge>
        </div>
        <p className="mt-1 text-sm text-[var(--gc-text-secondary)]">{t('scan.subtitle')}</p>
      </header>

      {scanError && (
        <div role="alert" className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 dark:border-rose-900 dark:bg-rose-950/30">
          <AlertCircle size={18} className="mt-0.5 shrink-0 text-rose-600" />
          <p className="flex-1 text-sm leading-relaxed text-rose-800 dark:text-rose-200">{scanError}</p>
        </div>
      )}

      <div className="grid grid-cols-1 items-start gap-5 xl:grid-cols-[minmax(0,1.8fr)_minmax(320px,0.9fr)]">
        <Card padding="lg" className="min-w-0">
          <div className="mb-4 flex items-center justify-between gap-3 border-b border-[var(--gc-border-subtle)] pb-3">
            <div>
              <h2 className="text-sm font-semibold text-[var(--gc-text-primary)]">{t('scan.yourRepos')}</h2>
              <p className="mt-0.5 text-xs text-[var(--gc-text-secondary)]">{t('scan.repositoryPickerHint')}</p>
            </div>
            <Button onClick={loadRepos} disabled={reposLoading} variant="secondary" size="sm" className="shrink-0">
              <RefreshCw size={14} className={reposLoading ? 'animate-spin' : ''} />
              {t('scan.refresh')}
            </Button>
          </div>

          <div className="relative mb-3">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-[var(--gc-text-tertiary)]" />
            <Input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t('scan.searchPlaceholder')} className="bg-[var(--gc-bg-default)] py-2.5 pl-10 text-sm" />
          </div>

          {reposLoading ? (
            <div className="flex flex-col items-center justify-center py-16 text-[var(--gc-text-secondary)]">
              <Loader2 size={24} className="mb-3 animate-spin text-emerald-700" />
              <p className="text-sm">{t('scan.loadingRepos')}</p>
            </div>
          ) : reposError ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle size={22} className="text-rose-500 mb-2" />
              <p className="max-w-sm text-sm text-[var(--gc-text-secondary)]">{reposError}</p>
              <Button onClick={loadRepos} variant="secondary" size="sm" className="mt-3">{t('scan.retrySync')}</Button>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <GitBranch size={24} className="mb-2 text-[var(--gc-text-tertiary)]" />
              <p className="font-mono text-sm text-[var(--gc-text-secondary)]">
                {repos.length === 0 ? t('scan.noReposToken') : t('scan.noReposMatch')}
              </p>
            </div>
          ) : (
            <ul className="-mx-1 max-h-[min(58vh,42rem)] divide-y divide-[var(--gc-border-subtle)] overflow-y-auto pr-1">
              {filtered.map((repo) => {
                const isSelected = selected?.full_name === repo.full_name;
                return (
                  <li key={repo.full_name}>
                    <button
                      type="button"
                      aria-pressed={isSelected}
                      onClick={() => selectRepo(repo)}
                      className={`w-full rounded-xl px-3 py-3 text-left transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-600 ${
                        isSelected
                          ? 'my-1 bg-emerald-50 ring-1 ring-emerald-600 dark:bg-emerald-950/30'
                          : 'hover:bg-[var(--gc-bg-subtle)]'
                      }`}
                    >
                      <div className="flex items-start gap-3.5">
                        <div className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${isSelected ? 'bg-emerald-900 text-emerald-50' : 'bg-[var(--gc-bg-subtle)] text-[var(--gc-text-secondary)]'}`}>
                          <GitBranch size={17} />
                        </div>
                        <div className="min-w-0 flex-1">
                          <div className="flex items-center gap-2 flex-wrap">
                            <span className="truncate font-mono text-sm font-semibold text-[var(--gc-text-primary)]">{repo.full_name}</span>
                            {repo.private ? <Lock size={12} aria-label="Private repository" className="shrink-0 text-amber-600" /> : <Globe size={12} aria-label="Public repository" className="shrink-0 text-[var(--gc-text-tertiary)]" />}
                            {repo.archived && <Badge variant="default" className="rounded-full bg-[var(--gc-bg-subtle)] px-2 py-0.5 text-[10px] font-semibold text-[var(--gc-text-secondary)]">{t('scan.archived')}</Badge>}
                          </div>
                          {repo.description && <p className="mt-1 truncate text-xs text-[var(--gc-text-secondary)]">{repo.description}</p>}
                          <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 font-mono text-[11px] text-[var(--gc-text-secondary)]">
                            <span className="rounded-md bg-[var(--gc-bg-subtle)] px-2 py-0.5">{repo.language}</span>
                            <span className="flex items-center gap-1"><GitBranch size={11} /> {repo.default_branch}</span>
                            <span>{formatSize(repo.size_kb)}</span>
                            {repo.stars > 0 && <span className="flex items-center gap-1"><Star size={11} /> {repo.stars}</span>}
                          </div>
                        </div>
                        {isSelected && <CheckCircle2 size={18} className="mt-1 shrink-0 text-emerald-700 dark:text-emerald-300" />}
                      </div>
                    </button>
                  </li>
                );
              })}
            </ul>
          )}
        </Card>

        <div className="space-y-5">
          <Card padding="lg" className="xl:sticky xl:top-2">
            <h2 className="mb-4 border-b border-[var(--gc-border-subtle)] pb-3 text-sm font-semibold text-[var(--gc-text-primary)]">
              {t('scan.auditConfig')}
            </h2>
            {selected ? (
              <div className="space-y-4">
                <div className="rounded-xl bg-[var(--gc-bg-subtle)] p-3.5">
                  <p className="label mb-1">{t('scan.selectedRepo')}</p>
                  <p className="truncate font-mono text-sm font-semibold text-[var(--gc-text-primary)]">{selected.full_name}</p>
                </div>
                <div>
                  <label className="label mb-1.5 block" htmlFor="ref-select">{t('scan.targetBranch')}</label>
                  <div className="relative">
                    <Select id="ref-select" value={ref} onChange={(e) => setRef(e.target.value)} className="appearance-none bg-[var(--gc-bg-default)] py-2.5 pr-9 font-mono text-sm">
                      {branches.length === 0 && <option value={ref}>{ref || selected.default_branch}</option>}
                      {branches.map((b) => <option key={b} value={b}>{b}</option>)}
                    </Select>
                    <ChevronDown size={15} className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-[var(--gc-text-tertiary)]" />
                  </div>
                  {branchesLoading && <p className="mt-1.5 flex items-center gap-1.5 text-xs text-[var(--gc-text-secondary)]"><Loader2 size={12} className="animate-spin" /> {t('scan.fetchingBranches')}</p>}
                  {branchesError && <p role="alert" className="mt-1.5 text-xs text-amber-700 dark:text-amber-300">{branchesError} {t('scan.branchLoadUsesDefault')}</p>}
                </div>
                <Button onClick={handleScan} disabled={isScanning} variant="primary" size="lg" className="w-full shadow-sm">
                  {isScanning ? (<><Loader2 size={14} className="animate-spin text-white" /> {t('scan.auditingCode')}</>) : (<><ArrowRight size={14} /> {t('scan.startAudit')}</>)}
                </Button>
                <Button onClick={handlePairAlexa} disabled={isPairing} variant="secondary" size="md" className="w-full">
                  {isPairing ? <Loader2 size={14} className="animate-spin" /> : <Link2 size={14} />}
                  {isPairing ? 'Generating code...' : 'Pair Alexa with this repository'}
                </Button>
                {pairingCode && (
                  <div className="rounded-xl border border-emerald-300 bg-emerald-50 p-3.5 dark:border-emerald-800 dark:bg-emerald-950/30">
                    <p className="text-xs font-semibold text-emerald-900 dark:text-emerald-200">Alexa pairing code (valid for 10 minutes)</p>
                    <p className="my-2 text-center font-mono text-2xl font-bold tracking-[0.3em] text-emerald-900 dark:text-emerald-100">{pairingCode}</p>
                    <p className="text-xs leading-relaxed text-emerald-800 dark:text-emerald-300">
                      Open GreenCode Auditor in Alexa and say: “link my GreenCode account with code {pairingCode}”.
                    </p>
                  </div>
                )}
                {pairingError && <p role="alert" className="text-xs text-rose-700 dark:text-rose-300">{pairingError}</p>}
              </div>
            ) : (
              <div className="rounded-xl border border-dashed border-[var(--gc-border-default)] px-4 py-8 text-center">
                <Cpu size={24} className="mx-auto mb-3 text-[var(--gc-text-tertiary)]" />
                <p className="text-sm text-[var(--gc-text-secondary)]">{t('scan.selectRepo')}</p>
              </div>
            )}
          </Card>

          {isScanning && (
            <Card padding="sm" className="border-olive-300 bg-olive-50/70 dark:bg-olive-900/20">
              <div className="flex items-start gap-3">
                <Loader2 size={16} className="mt-0.5 shrink-0 animate-spin text-emerald-700" />
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-[var(--gc-text-primary)]">{t('scan.auditInProgress')}</p>
                  <p className="mt-1 break-words text-xs text-[var(--gc-text-secondary)]">{statusMessage || t('scan.analyzingSource')}</p>
                </div>
              </div>
            </Card>
          )}

          <Card padding="lg">
            <h3 className="mb-3 text-sm font-semibold text-[var(--gc-text-primary)]">{t('scan.whatWeCheck')}</h3>
            <ul className="space-y-3 text-sm leading-relaxed text-[var(--gc-text-secondary)]">
              <li className="flex gap-2.5"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" /> {t('scan.check.nestedLoops')}</li>
              <li className="flex gap-2.5"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" /> {t('scan.check.dbQueries')}</li>
              <li className="flex gap-2.5"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" /> {t('scan.check.payloads')}</li>
              <li className="flex gap-2.5"><CheckCircle2 size={16} className="mt-0.5 shrink-0 text-emerald-700 dark:text-emerald-300" /> {t('scan.check.gridEmissions', { zone: activeZone })}</li>
            </ul>
          </Card>
        </div>
      </div>
    </div>
  );
}
