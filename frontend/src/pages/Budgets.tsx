import React, { useCallback, useEffect, useState } from 'react';
import { Plus, CheckCircle2 } from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import { authHeaders } from '../services/api';
import { useTenant } from '../context/TenantContext';

interface BudgetApiRow {
  team_id: string;
  monthly_budget_kg: number;
  current_consumed_kg: number;
  daily_burn_rate_kg: number;
  forecast_month_end_kg: number;
  alert_level: string;
}

interface TeamBudgetRow {
  team: string;
  limitKg: number;
  consumedKg: number;
  dailyBurnKg: number;
  forecastMonthEndKg: number;
  burnRate: string;
  status: string;
  pct: number;
}

interface SimResult {
  verdict: string;
  reason: string;
  projectedPct: number;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function requiredNumber(value: unknown, field: string): number {
  if (value === null || value === undefined || value === '') {
    throw new Error(`Budget response is missing a valid ${field}.`);
  }
  const number = typeof value === 'number' ? value : Number(value);
  if (!Number.isFinite(number)) throw new Error(`Budget response is missing a valid ${field}.`);
  return number;
}

function mapBudgetRows(rawList: unknown[], translate: ReturnType<typeof useT>): TeamBudgetRow[] {
  return rawList.map((raw) => {
    if (!isObject(raw) || typeof raw.team_id !== 'string' || !raw.team_id.trim()) {
      throw new Error('Budget response contains an invalid team entry.');
    }
    const limitKg = requiredNumber(raw.monthly_budget_kg, 'monthly budget');
    const consumedKg = requiredNumber(raw.current_consumed_kg, 'consumption');
    const dailyBurnKg = requiredNumber(raw.daily_burn_rate_kg, 'daily burn rate');
    const forecastMonthEndKg = requiredNumber(raw.forecast_month_end_kg, 'month-end forecast');
    const pct = limitKg > 0 ? (consumedKg / limitKg) * 100 : 0;
    if (typeof raw.alert_level !== 'string') {
      throw new Error(`Budget response for '${raw.team_id}' is missing its alert level.`);
    }
    return {
      team: raw.team_id,
      limitKg,
      consumedKg,
      dailyBurnKg,
      forecastMonthEndKg,
      burnRate: translate('budgets.burnRate', { rate: dailyBurnKg.toFixed(2) }),
      status: raw.alert_level,
      pct,
    };
  });
}

async function responseJson(response: Response): Promise<unknown> {
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = isObject(data) && typeof data.detail === 'string' ? data.detail : `HTTP ${response.status}`;
    throw new Error(detail);
  }
  return data;
}

export default function Budgets() {
  const t = useT();
  const { currentOrg, isLoading: tenantLoading } = useTenant();
  const [teamBudgets, setTeamBudgets] = useState<TeamBudgetRow[]>([]);
  const [newTeamName, setNewTeamName] = useState('');
  const [newTeamQuotaKg, setNewTeamQuotaKg] = useState('');
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [allocating, setAllocating] = useState(false);
  const [allocationMsg, setAllocationMsg] = useState<string | null>(null);
  const [allocationError, setAllocationError] = useState<string | null>(null);
  const [selectedSimTeam, setSelectedSimTeam] = useState('');
  const [prEmissionsInput, setPrEmissionsInput] = useState('');
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState<string | null>(null);
  const [simResult, setSimResult] = useState<SimResult | null>(null);

  const loadBudgets = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setLoadError(null);
    setTeamBudgets([]);
    setSelectedSimTeam('');
    setSimResult(null);
    try {
      const response = await fetch(`/api/energy/budgets?org_id=${currentOrg?.id}`, { headers: authHeaders(), signal });
      const data = await responseJson(response);
      if (!isObject(data) || !Array.isArray(data.budgets)) {
        throw new Error(t('budgets.invalidResponse'));
      }
      const rows = mapBudgetRows(data.budgets, t);
      setTeamBudgets(rows);
      setSelectedSimTeam((current) => (
        rows.some((row) => row.team === current) ? current : rows[0]?.team || ''
      ));
    } catch (error) {
      if (signal?.aborted) return;
      setTeamBudgets([]);
      setLoadError(error instanceof Error ? error.message : t('budgets.loadError'));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [currentOrg?.id, t]);

  useEffect(() => {
    if (tenantLoading) return;
    if (!currentOrg) {
      setLoading(false);
      setLoadError(t('budgets.organizationRequired'));
      return;
    }
    const controller = new AbortController();
    void loadBudgets(controller.signal);
    return () => controller.abort();
  }, [currentOrg?.id, loadBudgets, tenantLoading, t]);

  const handleAllocateBudget = async (event: React.FormEvent) => {
    event.preventDefault();
    const cleanTeam = newTeamName.trim();
    const quota = Number(newTeamQuotaKg);
    if (!cleanTeam || !Number.isFinite(quota) || quota <= 0) {
      setAllocationError(t('budgets.invalidAllocation'));
      setAllocationMsg(null);
      return;
    }

    setAllocating(true);
    setAllocationMsg(null);
    setAllocationError(null);
    try {
      const response = await fetch('/api/energy/budgets/allocate', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ org_id: currentOrg?.id, team_id: cleanTeam, monthly_budget_kg: quota }),
      });
      const data = await responseJson(response);
      if (!isObject(data) || data.success !== true || !Array.isArray(data.budgets)) {
        throw new Error(t('budgets.invalidAllocationResponse'));
      }
      setTeamBudgets(mapBudgetRows(data.budgets, t));
      setSelectedSimTeam(cleanTeam);
      setAllocationMsg(t('budgets.allocated', { team: cleanTeam, quota: quota.toFixed(1) }));
      setNewTeamName('');
      setNewTeamQuotaKg('');
    } catch (error) {
      setAllocationError(error instanceof Error ? error.message : t('budgets.loadError'));
    } finally {
      setAllocating(false);
    }
  };

  useEffect(() => {
    if (!currentOrg || !selectedSimTeam || !teamBudgets.some((budget) => budget.team === selectedSimTeam) || prEmissionsInput === '') {
      setSimResult(null);
      setSimError(null);
      setSimLoading(false);
      return;
    }
    const projectedEmissions = Number(prEmissionsInput);
    if (!Number.isFinite(projectedEmissions) || projectedEmissions < 0) {
      setSimResult(null);
      setSimError(t('budgets.invalidProjection'));
      return;
    }

    const controller = new AbortController();
    const evaluate = async () => {
      setSimLoading(true);
      setSimError(null);
      setSimResult(null);
      try {
        const response = await fetch('/api/energy/budgets/evaluate-pr', {
          method: 'POST',
          headers: authHeaders({ 'Content-Type': 'application/json' }),
          body: JSON.stringify({
            org_id: currentOrg?.id,
            team_id: selectedSimTeam,
            additional_projected_kg_co2e: projectedEmissions,
          }),
          signal: controller.signal,
        });
        const data = await responseJson(response);
        if (!isObject(data) || typeof data.verdict !== 'string' || typeof data.reason !== 'string') {
          throw new Error(t('budgets.invalidEvaluationResponse'));
        }
        setSimResult({
          verdict: data.verdict,
          reason: data.reason,
          projectedPct: requiredNumber(data.projected_consumption_pct, 'projected consumption'),
        });
      } catch (error) {
        if (!controller.signal.aborted) {
          setSimError(error instanceof Error ? error.message : t('budgets.evaluationError'));
        }
      } finally {
        if (!controller.signal.aborted) setSimLoading(false);
      }
    };
    void evaluate();
    return () => controller.abort();
  }, [currentOrg?.id, prEmissionsInput, selectedSimTeam, t, teamBudgets]);

  const totalQuotaKg = teamBudgets.reduce((acc, team) => acc + team.limitKg, 0);
  const totalConsumedKg = teamBudgets.reduce((acc, team) => acc + team.consumedKg, 0);
  const totalForecastKg = teamBudgets.reduce((acc, team) => acc + team.forecastMonthEndKg, 0);
  const totalPct = totalQuotaKg > 0 ? (totalConsumedKg / totalQuotaKg) * 100 : 0;

  return (
    <div className="space-y-5">
      <div className="card p-5 space-y-4">
        <div>
          <h1 className="text-lg font-semibold text-zinc-950 tracking-tight">{t('budgets.title')}</h1>
          <p className="text-xs text-zinc-500 mt-0.5">{currentOrg?.name || t('budgets.organizationRequired')}</p>
          <p className="text-xs text-zinc-500 mt-1">{t('budgets.subtitle')}</p>
        </div>

        <form onSubmit={handleAllocateBudget} className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-zinc-100 dark:border-slate-700 items-end">
          <div>
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">
              {t('budgets.teamIdentifier')}
            </label>
            <input
              type="text"
              value={newTeamName}
              onChange={(event) => setNewTeamName(event.target.value)}
              placeholder={t('budgets.teamPlaceholder')}
              className="input font-mono"
              required
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">
              {t('budgets.monthlyQuota')}
            </label>
            <input
              type="number"
              step="any"
              min="0.01"
              value={newTeamQuotaKg}
              onChange={(event) => setNewTeamQuotaKg(event.target.value)}
              className="input font-mono"
              required
            />
          </div>
          <button
            type="submit"
            disabled={allocating || !currentOrg}
            className="btn-primary text-xs px-3.5 py-2 flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> {allocating ? t('budgets.saving') : t('budgets.allocateButton')}
          </button>
        </form>

        {allocationError && <p role="alert" className="text-xs text-red-700">{allocationError}</p>}
        {allocationMsg && (
          <div role="status" className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3.5 py-2.5 rounded-lg flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{allocationMsg}</span>
          </div>
        )}
      </div>

      {loadError && (
        <div role="alert" className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800">
          {loadError}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.totalQuota')}</span>
          <div className="text-2xl font-semibold font-mono text-zinc-950 dark:text-zinc-100 mt-1.5">
            {loading ? t('budgets.loading') : teamBudgets.length ? `${totalQuotaKg.toFixed(1)} kg CO₂e` : t('budgets.notAvailable')}
          </div>
          <span className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1.5 block">
            {t('budgets.kpi.allocatedTeams', { count: teamBudgets.length })}
          </span>
        </div>
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.consumed')}</span>
          <div className="text-2xl font-semibold font-mono text-zinc-950 dark:text-zinc-100 mt-1.5">
            {loading ? t('budgets.loading') : teamBudgets.length ? `${totalConsumedKg.toFixed(2)} kg CO₂e` : t('budgets.notAvailable')}
          </div>
          {teamBudgets.length > 0 && (
            <span className="text-[11px] font-mono text-emerald-700 mt-1.5 block">
              {totalPct.toFixed(1)}% {t('budgets.kpi.totalConsumption')}
            </span>
          )}
        </div>
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.forecast')}</span>
          <div className="text-2xl font-semibold font-mono text-amber-600 mt-1.5">
            {loading ? t('budgets.loading') : teamBudgets.length ? `${totalForecastKg.toFixed(2)} kg CO₂e` : t('budgets.notAvailable')}
          </div>
          {teamBudgets.length > 0 && (
            <span className="text-[11px] font-mono text-amber-700 mt-1.5 block">
              {totalForecastKg > totalQuotaKg
                ? t('budgets.kpi.overrun', { amount: (totalForecastKg - totalQuotaKg).toFixed(2) })
                : t('budgets.kpi.underQuota', { amount: Math.max(0, totalQuotaKg - totalForecastKg).toFixed(2) })}
            </span>
          )}
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">{t('budgets.tableTitle')}</h2>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">{t('budgets.alertsInfo')}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs uppercase border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-5 py-3.5">{t('budgets.table.team')}</th>
                <th className="px-5 py-3.5">{t('budgets.table.quota')}</th>
                <th className="px-5 py-3.5">{t('budgets.table.consumed')}</th>
                <th className="px-5 py-3.5">{t('budgets.table.dailyBurn')}</th>
                <th className="px-5 py-3.5">{t('budgets.table.quotaMeter')}</th>
                <th className="px-5 py-3.5">{t('budgets.table.alertLevel')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {teamBudgets.map((row) => (
                <tr key={row.team} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                  <td className="px-5 py-4 font-semibold text-slate-900 dark:text-slate-100">{row.team}</td>
                  <td className="px-5 py-4 text-slate-600 dark:text-slate-400">{row.limitKg.toFixed(1)} kg</td>
                  <td className="px-5 py-4 text-slate-900 dark:text-slate-300 font-medium">{row.consumedKg.toFixed(2)} kg</td>
                  <td className="px-5 py-4 text-slate-500 dark:text-slate-400">{row.burnRate}</td>
                  <td className="px-5 py-4 w-48">
                    <div className="h-2 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${row.pct >= 100 ? 'bg-red-500' : row.pct >= 90 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                        style={{ width: `${Math.min(100, row.pct)}%` }}
                      />
                    </div>
                    <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">{row.pct.toFixed(1)}%</span>
                  </td>
                  <td className="px-5 py-4">
                    <span className={`px-2.5 py-1 text-xs rounded-full font-semibold ${
                      row.status === 'BREACHED' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200'
                        : row.status === 'CRITICAL' || row.status === 'WARNING' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-200'
                          : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-200'
                    }`}>
                      {t(`budgets.status.${row.status.toLowerCase()}`)}
                    </span>
                  </td>
                </tr>
              ))}
              {!teamBudgets.length && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-500">
                    {loading ? t('budgets.loading') : t('budgets.empty')}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-emerald-400">{t('budgets.simulator.title')}</h3>
        <p className="text-xs text-slate-400 mt-1">{t('budgets.simulator.description')}</p>
        {!teamBudgets.length ? (
          <p className="text-sm text-slate-300 mt-4">{t('budgets.simulator.noBudgets')}</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 items-end">
            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">{t('budgets.simulator.targetTeam')}</label>
              <select
                value={selectedSimTeam}
                onChange={(event) => setSelectedSimTeam(event.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none"
              >
                {teamBudgets.map((budget) => (
                  <option key={budget.team} value={budget.team}>
                    {budget.team} ({budget.consumedKg.toFixed(1)} / {budget.limitKg.toFixed(1)} kg used)
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-300 font-medium block mb-1">{t('budgets.simulator.projectedEmission')}</label>
              <input
                type="number"
                step="any"
                min="0"
                value={prEmissionsInput}
                onChange={(event) => setPrEmissionsInput(event.target.value)}
                className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none"
              />
            </div>
            <div className="p-3 rounded-lg bg-slate-800 border border-slate-700">
              <span className="text-xs text-slate-400 block font-medium">
                {t('budgets.simulator.mergeGateVerdict', { pct: simResult?.projectedPct.toFixed(1) || '' })}
              </span>
              <span
                className={`text-sm font-bold ${
                  simResult?.verdict === 'BLOCKED' ? 'text-red-400'
                    : simResult?.verdict === 'WARNING' ? 'text-amber-400'
                      : 'text-emerald-400'
                }`}
              >
                {simLoading ? t('budgets.simulator.evaluating') : simError || (simResult
                  ? `${simResult.verdict} - ${simResult.reason}`
                  : t('budgets.simulator.enterProjection'))}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
