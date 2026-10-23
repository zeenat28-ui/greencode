import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Activity, ArrowDownRight, ArrowUpRight, Building2, DollarSign, Leaf, RefreshCw, TrendingDown,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { useT } from '../i18n/I18nContext';
import { useTenant } from '../context/TenantContext';
import { authHeaders } from '../services/api';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';

type ApiObject = Record<string, unknown>;

interface OverviewRepository extends ApiObject {
  id?: number | string;
  name?: string | null;
  repo_name?: string | null;
  full_name?: string | null;
  path_or_url?: string | null;
  source?: string | null;
  team_id?: string | null;
}

interface OverviewWorkloads {
  healthy: number | null;
  total: number | null;
  source: string | null;
  annualCostUsd: number | null;
  annualCo2Kg: number | null;
}

function isObject(value: unknown): value is ApiObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function optionalNumber(value: unknown): number | null {
  if (value === null || value === undefined || value === '') return null;
  const number = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(number) ? number : null;
}

async function fetchJson(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(path, { headers: authHeaders(), signal });
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const rawDetail = isObject(data) ? data.detail : null;
    const detail = typeof rawDetail === 'string'
      ? rawDetail
      : Array.isArray(rawDetail) && isObject(rawDetail[0]) && typeof rawDetail[0].msg === 'string'
        ? `${rawDetail[0].msg}${Array.isArray(rawDetail[0].loc) ? ` (${rawDetail[0].loc.join('.')})` : ''}`
        : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

export default function Overview() {
  const t = useT();
  const { currentOrg, isLoading: tenantLoading } = useTenant();
  const [selectedTeam, setSelectedTeam] = useState('all');
  const [liveRepos, setLiveRepos] = useState<OverviewRepository[]>([]);
  const [teams, setTeams] = useState<string[]>([]);
  const [quotaStats, setQuotaStats] = useState<{ consumed: number; limit: number } | null>(null);
  const [workloadSummary, setWorkloadSummary] = useState<OverviewWorkloads | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(true);
  const [overviewErrors, setOverviewErrors] = useState<string[]>([]);
  const [exportingReport, setExportingReport] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const requestVersion = useRef(0);
  const activeRequest = useRef<AbortController | null>(null);

  const loadOverviewData = useCallback(async () => {
    if (!currentOrg) {
      setOverviewLoading(false);
      return;
    }
    const requestId = ++requestVersion.current;
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    setOverviewLoading(true);
    setOverviewErrors([]);
    const errors: string[] = [];
    const load = async (path: string, onSuccess: (data: unknown) => void, invalidResponse: string) => {
      try {
        const data = await fetchJson(path, controller.signal);
        if (requestId !== requestVersion.current) return;
        onSuccess(data);
      } catch (error) {
        if (!controller.signal.aborted) {
          errors.push(error instanceof Error ? error.message : invalidResponse);
        }
      }
    };

    await Promise.all([
      load('/api/repositories?limit=100', (data) => {
        if (isObject(data) && Array.isArray(data.repositories)) {
          setLiveRepos(data.repositories.filter(isObject) as OverviewRepository[]);
        } else {
          errors.push(t('overview.invalidRepositories'));
        }
      }, t('overview.invalidRepositories')),
      load(`/api/energy/budgets?org_id=${currentOrg?.id}`, (data) => {
        if (!isObject(data) || !Array.isArray(data.budgets)) {
          errors.push(t('overview.invalidBudgets'));
          return;
        }
        const rows = data.budgets.filter(isObject);
        const discoveredTeams = rows
          .map((budget) => budget.team_id)
          .filter((team): team is string => typeof team === 'string' && team.trim().length > 0);
        setTeams(discoveredTeams);
        setSelectedTeam((current) => (
          current === 'all' || discoveredTeams.includes(current) ? current : 'all'
        ));
        const limitValues = rows.map((budget) => optionalNumber(budget.monthly_budget_kg));
        const consumedValues = rows.map((budget) => optionalNumber(budget.current_consumed_kg));
        if (rows.length && limitValues.every((value): value is number => value !== null)
            && consumedValues.every((value): value is number => value !== null)) {
          setQuotaStats({
            limit: limitValues.reduce((sum, value) => sum + value, 0),
            consumed: consumedValues.reduce((sum, value) => sum + value, 0),
          });
        } else {
          setQuotaStats(null);
        }
      }, t('overview.invalidBudgets')),
      load('/api/energy/workloads?limit=12', (data) => {
        if (!isObject(data)) {
          errors.push(t('overview.invalidWorkloads'));
          return;
        }
        setWorkloadSummary({
          healthy: optionalNumber(data.healthy_workloads),
          total: optionalNumber(data.total_workloads),
          source: typeof data.telemetry_source === 'string' ? data.telemetry_source : null,
          annualCostUsd: optionalNumber(data.total_annual_cost_usd),
          annualCo2Kg: optionalNumber(data.total_annual_co2_kg),
        });
      }, t('overview.invalidWorkloads')),
    ]);

    if (requestId !== requestVersion.current) return;
    setOverviewErrors(errors);
    setOverviewLoading(false);
    setLastUpdated(new Date());
    activeRequest.current = null;
  }, [currentOrg?.id, t]);

  useEffect(() => {
    if (tenantLoading) return;
    if (!currentOrg) {
      setOverviewLoading(false);
      return;
    }
    void loadOverviewData();
    return () => {
      requestVersion.current += 1;
      activeRequest.current?.abort();
    };
  }, [currentOrg?.id, loadOverviewData, tenantLoading]);

  const handleExportDisclosure = async () => {
    if (!currentOrg) return;
    setExportingReport(true);
    setOverviewErrors([]);
    try {
      const response = await fetch('/api/enterprise/compliance/esg-disclosure', { headers: authHeaders() });
      if (!response.ok) {
        const data: unknown = await response.json().catch(() => null);
        const detail = isObject(data) && typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`;
        throw new Error(detail);
      }
      const payload = await response.json();
      const report = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(report);
      const link = document.createElement('a');
      link.href = url;
      link.download = `greencode-esg-report-${currentOrg.slug}.json`;
      link.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setOverviewErrors([error instanceof Error ? error.message : t('overview.exportError')]);
    } finally {
      setExportingReport(false);
    }
  };

  const filteredRepos = liveRepos.filter((repo) => (
    selectedTeam === 'all' || repo.team_id?.toLowerCase() === selectedTeam.toLowerCase()
  ));
  const scores = filteredRepos
    .map((repo) => optionalNumber(repo.green_score))
    .filter((score): score is number => score !== null);
  const averageScore = scores.length
    ? scores.reduce((sum, score) => sum + score, 0) / scores.length
    : null;
  const totalViolations = filteredRepos
    .map((repo) => optionalNumber(repo.total_violations))
    .filter((count): count is number => count !== null)
    .reduce((sum, count) => sum + count, 0);

  return (
    <div className="mx-auto max-w-[1440px] space-y-5 pb-4">
      <section className="relative isolate overflow-hidden rounded-2xl bg-[#102c21] px-5 py-6 text-white shadow-[0_16px_40px_rgba(16,44,33,0.14)] sm:px-7 sm:py-7">
        <div className="pointer-events-none absolute -right-16 -top-24 -z-10 h-72 w-72 rounded-full border border-emerald-200/10" />
        <div className="pointer-events-none absolute -right-4 -top-12 -z-10 h-52 w-52 rounded-full border border-emerald-200/10" />
        <div className="flex flex-col justify-between gap-6 lg:flex-row lg:items-end">
          <div className="min-w-0">
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-emerald-200/20 bg-emerald-200/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.13em] text-emerald-100">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
                {t('overview.tenantIsolated')}
              </span>
              {currentOrg && (
                <span className="text-[11px] font-mono text-emerald-100/65">
                  {t('overview.organizationId', { id: String(currentOrg.id) })}
                </span>
              )}
            </div>
            <p className="mb-1 text-xs font-medium tracking-wide text-emerald-100/70">{t('overview.dashboardEyebrow')}</p>
            <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
              {currentOrg?.name || t('overview.organizationRequired')}
            </h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-emerald-50/70">{t('overview.orgSubtitle')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor="overview-team-filter">{t('overview.teamFilter')}</label>
            <select
              id="overview-team-filter"
              value={selectedTeam}
              onChange={(event) => setSelectedTeam(event.target.value)}
              className="min-h-10 rounded-lg border border-white/15 bg-white/10 px-3 text-xs font-medium text-white outline-none transition hover:bg-white/15 focus:border-emerald-200/60 focus:ring-2 focus:ring-emerald-200/20 disabled:opacity-50"
              disabled={!teams.length}
            >
              <option className="text-slate-900" value="all">{t('overview.allTeams')}</option>
              {teams.map((team) => <option className="text-slate-900" key={team} value={team}>{team}</option>)}
            </select>
            <button
              type="button"
              onClick={() => void loadOverviewData()}
              disabled={!currentOrg}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3.5 text-xs font-semibold text-white transition hover:bg-white/15 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <RefreshCw size={14} className={overviewLoading ? 'animate-spin' : ''} />
              {t('overview.refresh')}
            </button>
            <button
              type="button"
              onClick={handleExportDisclosure}
              disabled={exportingReport || !currentOrg}
              className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg bg-emerald-300 px-3.5 text-xs font-bold text-[#102c21] shadow-sm transition hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {exportingReport ? t('overview.exportingEsgJson') : t('overview.exportEsgJson')}
              <ArrowUpRight size={14} />
            </button>
          </div>
        </div>
        <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-white/10 pt-4">
          <div className="flex items-center gap-2 text-xs text-emerald-50/70">
            <Leaf size={14} className="text-emerald-300" />
            <span>{t('overview.dashboardSummary', {
              repositories: String(filteredRepos.length),
              violations: String(totalViolations),
            })}</span>
          </div>
          <span className="text-[11px] text-emerald-50/50">
            {lastUpdated ? t('overview.lastUpdated', { time: lastUpdated.toLocaleTimeString() }) : t('overview.awaitingData')}
          </span>
        </div>
      </section>

      {overviewErrors.length > 0 && (
        <div role="alert" className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          <p className="font-semibold">{t('overview.loadError')}</p>
          <ul className="mt-1 list-disc pl-5">
            {overviewErrors.map((error, index) => <li key={`${index}-${error}`}>{error}</li>)}
          </ul>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="card group p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-start justify-between gap-3">
            <div className="text-xs font-medium text-[var(--gc-text-secondary)]">{t('overview.carbonQuota')}</div>
            <span className="rounded-lg bg-emerald-50 p-2 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
              <Building2 className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 text-2xl font-semibold tracking-tight font-mono text-[var(--gc-text-primary)]">
            {overviewLoading ? t('overview.loadingMetrics') : quotaStats ? `${quotaStats.consumed.toFixed(2)} / ${quotaStats.limit.toFixed(1)} kg` : t('overview.notAvailable')}
          </div>
          {quotaStats && (
            <div className="mt-2.5">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--gc-bg-subtle)]">
                <div
                  className="h-full bg-emerald-600 rounded-full"
                  style={{ width: `${Math.min(100, Math.round((quotaStats.consumed / Math.max(1, quotaStats.limit)) * 100))}%` }}
                />
              </div>
              <div className="mt-1.5 flex justify-between text-[11px] font-mono text-[var(--gc-text-tertiary)]">
                <span>{t('overview.quotaPct', { pct: String(Math.min(100, Math.round((quotaStats.consumed / Math.max(1, quotaStats.limit)) * 100))) })}</span>
                <span>{t('overview.quotaFree', { kg: Math.max(0, quotaStats.limit - quotaStats.consumed).toFixed(1) })}</span>
              </div>
            </div>
          )}
        </div>

        <div className="card group p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-start justify-between gap-3">
            <div className="text-xs font-medium text-[var(--gc-text-secondary)]">{t('overview.runtimeWorkloads')}</div>
            <span className="rounded-lg bg-sky-50 p-2 text-sky-700 dark:bg-sky-950/50 dark:text-sky-300">
              <Activity className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 text-2xl font-semibold tracking-tight font-mono text-[var(--gc-text-primary)]">
            {overviewLoading ? t('overview.loadingMetrics') : workloadSummary && workloadSummary.healthy !== null && workloadSummary.total !== null
              ? t('overview.healthyCount', { healthy: String(workloadSummary.healthy), total: String(workloadSummary.total) })
              : t('overview.notAvailable')}
          </div>
          {workloadSummary?.source && (
            <p className="mt-2 text-[11px] font-mono text-emerald-700 dark:text-emerald-300">
              {t('overview.sourceLabel', { source: workloadSummary.source })}
            </p>
          )}
        </div>

        <div className="card group p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-start justify-between gap-3">
            <div className="text-xs font-medium text-[var(--gc-text-secondary)]">{t('overview.runtimeDraw')}</div>
            <span className="rounded-lg bg-amber-50 p-2 text-amber-700 dark:bg-amber-950/50 dark:text-amber-300">
              <DollarSign className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 text-2xl font-semibold tracking-tight font-mono text-[var(--gc-text-primary)]">
            {overviewLoading ? t('overview.loadingMetrics') : workloadSummary?.annualCostUsd !== null && workloadSummary?.annualCostUsd !== undefined
              ? t('overview.annualCost', { cost: workloadSummary.annualCostUsd.toFixed(2) })
              : t('overview.notAvailable')}
          </div>
          {workloadSummary?.annualCo2Kg !== null && workloadSummary?.annualCo2Kg !== undefined && (
            <p className="mt-2 flex items-center gap-1 text-[11px] font-mono text-[var(--gc-text-tertiary)]">
              <TrendingDown className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-300" />
              <span>{t('overview.co2Yearly', { co2: workloadSummary.annualCo2Kg.toFixed(1) })}</span>
            </p>
          )}
        </div>

        <div className="card group p-4 transition duration-200 hover:-translate-y-0.5 hover:shadow-md">
          <div className="flex items-start justify-between gap-3">
            <div className="text-xs font-medium text-[var(--gc-text-secondary)]">{t('overview.auditHealth')}</div>
            <span className="rounded-lg bg-violet-50 p-2 text-violet-700 dark:bg-violet-950/50 dark:text-violet-300">
              <Leaf className="h-4 w-4" />
            </span>
          </div>
          <div className="mt-3 text-2xl font-semibold tracking-tight font-mono text-[var(--gc-text-primary)]">
            {overviewLoading ? t('overview.loadingMetrics') : averageScore !== null ? `${averageScore.toFixed(1)} / 100` : t('overview.notAvailable')}
          </div>
          <p className="mt-2 flex items-center gap-1 text-[11px] text-[var(--gc-text-tertiary)]">
            {totalViolations > 0
              ? <><ArrowDownRight className="h-3.5 w-3.5 text-amber-600 dark:text-amber-300" />{t('overview.findingsSummary', { count: String(totalViolations) })}</>
              : <>{t('overview.repositoriesAudited', { count: String(filteredRepos.length) })}</>}
          </p>
        </div>
      </div>

      <section aria-labelledby="alexa-mcp-demo-title" className="space-y-2">
        <div>
          <h2 id="alexa-mcp-demo-title" className="text-base font-semibold text-[var(--gc-text-primary)]">
            Alexa+ MCP web demo
          </h2>
          <p className="mt-1 text-xs text-[var(--gc-text-tertiary)]">
            Each query opens a real Streamable HTTP session, discovers the server tools, and invokes the selected GreenCode MCP tool.
          </p>
        </div>
        <AlexaVoiceCockpit />
      </section>

      <section className="overflow-hidden rounded-xl border border-[var(--gc-border-default)] bg-[var(--gc-bg-surface)] shadow-sm">
        <div className="flex flex-col justify-between gap-3 border-b border-[var(--gc-border-subtle)] px-4 py-4 sm:flex-row sm:items-center sm:px-5">
          <div>
            <h2 className="font-semibold text-[var(--gc-text-primary)] text-base">{t('overview.pageTitle', { count: String(filteredRepos.length) })}</h2>
            <p className="mt-1 text-xs text-[var(--gc-text-tertiary)]">{t('overview.ledgerHint')}</p>
          </div>
          <Link
            to="/scan"
            className="inline-flex min-h-9 items-center justify-center gap-2 rounded-lg border border-[var(--gc-border-default)] px-3 text-xs font-semibold text-[var(--gc-text-primary)] transition hover:border-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-300"
          >
            {t('overview.auditRepository')}
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-[var(--gc-border-subtle)] bg-[var(--gc-bg-subtle)] text-[10px] uppercase tracking-[0.08em] text-[var(--gc-text-tertiary)]">
              <tr>
                <th className="px-4 py-3 font-semibold sm:px-5">{t('overview.colServiceName')}</th>
                <th className="px-4 py-3 font-semibold sm:px-5">{t('overview.colFiles')}</th>
                <th className="px-4 py-3 font-semibold sm:px-5">{t('overview.colGreenScore')}</th>
                <th className="px-4 py-3 font-semibold sm:px-5">{t('overview.colViolations')}</th>
                <th className="px-4 py-3 font-semibold sm:px-5">{t('overview.colSource')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--gc-border-subtle)]">
              {filteredRepos.map((repo, index) => {
                const score = optionalNumber(repo.green_score);
                const fileCount = optionalNumber(repo.total_files);
                const lineCount = optionalNumber(repo.total_lines);
                const violationsCount = optionalNumber(repo.total_violations);
                const repoName = repo.repo_name || repo.full_name || repo.name || repo.path_or_url;
                return (
                  <tr key={repo.id ?? repo.path_or_url ?? `${repoName ?? 'repository'}-${index}`} className="transition-colors hover:bg-emerald-50/50 dark:hover:bg-emerald-950/20">
                    <td className="px-4 py-4 font-semibold text-[var(--gc-text-primary)] sm:px-5">{typeof repoName === 'string' ? repoName : t('overview.notAvailable')}</td>
                    <td className="px-4 py-4 text-[var(--gc-text-secondary)] sm:px-5">
                      {fileCount !== null && lineCount !== null
                        ? `${fileCount} files / ${lineCount.toLocaleString()} LOC`
                        : t('overview.notAvailable')}
                    </td>
                    <td className="px-4 py-4 font-bold text-emerald-700 dark:text-emerald-300 sm:px-5">
                      {score !== null ? `${score.toFixed(1)} / 100` : t('overview.notAvailable')}
                    </td>
                    <td className="px-4 py-4 text-[var(--gc-text-secondary)] sm:px-5">
                      {violationsCount !== null
                        ? t('overview.findingsCount', { count: String(violationsCount), plural: violationsCount === 1 ? '' : 's' })
                        : t('overview.notAvailable')}
                    </td>
                    <td className="px-4 py-4 text-[var(--gc-text-secondary)] sm:px-5">{typeof repo.source === 'string' ? repo.source : t('overview.notAvailable')}</td>
                  </tr>
                );
              })}
              {!filteredRepos.length && (
                <tr>
                  <td colSpan={5} className="px-5 py-12 text-center">
                    <div className="mx-auto mb-3 flex h-11 w-11 items-center justify-center rounded-full bg-emerald-50 text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
                      {overviewLoading ? <RefreshCw size={18} className="animate-spin" /> : <Leaf size={18} />}
                    </div>
                    <p className="font-medium text-[var(--gc-text-primary)]">
                      {overviewLoading ? t('overview.loadingRepositories') : t('overview.emptyTitle')}
                    </p>
                    {!overviewLoading && (
                      <p className="mx-auto mt-1 max-w-md text-xs leading-5 text-[var(--gc-text-tertiary)]">{t('overview.emptyBody')}</p>
                    )}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
