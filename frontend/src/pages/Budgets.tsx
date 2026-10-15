import React, { useState, useEffect, useCallback } from 'react';
import { Plus, CheckCircle2 } from 'lucide-react';
import { useT } from '../i18n/I18nContext';

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

export default function Budgets() {
  const t = useT();
  const [teamBudgets, setTeamBudgets] = useState<TeamBudgetRow[]>([]);
  const [newTeamName, setNewTeamName] = useState<string>('ml-platform');
  const [newTeamQuotaKg, setNewTeamQuotaKg] = useState<number>(400.0);
  const [allocating, setAllocating] = useState<boolean>(false);
  const [allocationMsg, setAllocationMsg] = useState<string | null>(null);

  const [selectedSimTeam, setSelectedSimTeam] = useState<string>('core-infra');
  const [prEmissionsInput, setPrEmissionsInput] = useState<number>(12.5);
  const [simResult, setSimResult] = useState<{
    verdict: string;
    reason: string;
    projectedPct: number;
  } | null>(null);

  const mapBudgetRows = useCallback((rawList: any[]): TeamBudgetRow[] => {
    return rawList.map((b: any) => {
      const limitKg = Number(b.monthly_budget_kg ?? b.monthly_budget_kg_co2e ?? 500.0);
      const consumedKg = Number(b.current_consumed_kg ?? b.consumed_kg_co2e ?? 0.0);
      const dailyBurnKg = Number(b.daily_burn_rate_kg ?? consumedKg / 30.0);
      const forecastMonthEndKg = Number(b.forecast_month_end_kg ?? dailyBurnKg * 30.0);
      const pct = limitKg > 0 ? (consumedKg / limitKg) * 100.0 : 0.0;
      const status = String(
        b.alert_level || (pct >= 100 ? 'BREACHED' : pct >= 90 ? 'CRITICAL' : pct >= 70 ? 'WARNING' : 'NORMAL')
      );
      return {
        team: String(b.team_id || 'core-infra'),
        limitKg,
        consumedKg,
        dailyBurnKg,
        forecastMonthEndKg,
        burnRate: t('budgets.burnRate', { rate: dailyBurnKg.toFixed(2) }),
        status,
        pct,
      };
    });
  }, []);

  const loadBudgets = useCallback(() => {
    fetch('/api/energy/budgets')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.budgets) && data.budgets.length > 0) {
          const rows = mapBudgetRows(data.budgets);
          setTeamBudgets(rows);
          if (rows.length > 0 && !rows.some((r) => r.team === selectedSimTeam)) {
            setSelectedSimTeam(rows[0].team);
          }
        }
      })
      .catch(() => {});
  }, [mapBudgetRows, selectedSimTeam]);

  useEffect(() => {
    loadBudgets();
  }, [loadBudgets]);

  const handleAllocateBudget = async (e: React.FormEvent) => {
    e.preventDefault();
    const cleanTeam = newTeamName.trim();
    if (!cleanTeam || newTeamQuotaKg <= 0) return;
    setAllocating(true);
    setAllocationMsg(null);
    try {
      const res = await fetch('/api/energy/budgets/allocate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          org_id: 1,
          team_id: cleanTeam,
          monthly_budget_kg: newTeamQuotaKg,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        if (Array.isArray(data.budgets)) {
          setTeamBudgets(mapBudgetRows(data.budgets));
        } else {
          loadBudgets();
        }
        setSelectedSimTeam(cleanTeam);
        setAllocationMsg(t('budgets.allocated', { team: cleanTeam, quota: newTeamQuotaKg.toFixed(1) }));
      }
    } catch {
      setAllocationMsg(t('budgets.couldNotAllocate', { team: cleanTeam }));
    } finally {
      setAllocating(false);
    }
  };

  useEffect(() => {
    if (!selectedSimTeam) return;
    fetch('/api/energy/budgets/evaluate-pr', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        org_id: 1,
        team_id: selectedSimTeam,
        additional_projected_kg_co2e: Math.max(0, prEmissionsInput),
      }),
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.verdict) {
          setSimResult({
            verdict: String(data.verdict),
            reason: String(data.reason || ''),
            projectedPct: Number(data.projected_consumption_pct ?? 0),
          });
        }
      })
      .catch(() => {});
  }, [selectedSimTeam, prEmissionsInput, teamBudgets]);

  const totalQuotaKg = teamBudgets.reduce((acc, t) => acc + t.limitKg, 0);
  const totalConsumedKg = teamBudgets.reduce((acc, t) => acc + t.consumedKg, 0);
  const totalForecastKg = teamBudgets.reduce((acc, t) => acc + t.forecastMonthEndKg, 0);
  const totalPct = totalQuotaKg > 0 ? (totalConsumedKg / totalQuotaKg) * 100.0 : 0.0;

  return (
    <div className="space-y-5">
      {/* Header & Allocation Form */}
      <div className="card p-5 space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-semibold text-zinc-950 tracking-tight">{t('budgets.title')}</h1>
              <span className="badge-olive">FOCUS 1.4</span>
            </div>
            <p className="text-xs text-zinc-500 mt-0.5">
              {t('budgets.subtitle')}
            </p>
          </div>
        </div>

        <form onSubmit={handleAllocateBudget} className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-zinc-100 dark:border-slate-700 items-end">
        <div>
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">
              {t('budgets.teamIdentifier')}
            </label>
            <input
              type="text"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              placeholder={t('budgets.teamPlaceholder')}
              className="input font-mono"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-zinc-700 dark:text-zinc-300 block mb-1">
              {t('budgets.monthlyQuota')}
            </label>
            <input
              type="number"
              step="10"
              min="1"
              value={newTeamQuotaKg}
              onChange={(e) => setNewTeamQuotaKg(Number(e.target.value))}
              className="input font-mono"
            />
          </div>
          <button
            type="submit"
            disabled={allocating}
            className="btn-primary text-xs px-3.5 py-2 flex items-center gap-1.5"
          >
            <Plus className="w-3.5 h-3.5" /> {allocating ? t('budgets.saving') : t('budgets.allocateButton')}
          </button>
        </form>

        {allocationMsg && (
          <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs px-3.5 py-2.5 rounded-lg flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
            <span>{allocationMsg}</span>
          </div>
        )}
      </div>

      {/* Grid Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.totalQuota')}</span>
          <div className="text-2xl font-semibold font-mono text-zinc-950 dark:text-zinc-100 mt-1.5">{totalQuotaKg.toFixed(1)} kg CO₂e</div>
          <span className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1.5 block">{t('budgets.kpi.allocatedTeams', { count: teamBudgets.length })}</span>
        </div>
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.consumed')}</span>
          <div className="text-2xl font-semibold font-mono text-zinc-950 dark:text-zinc-100 mt-1.5">{totalConsumedKg.toFixed(2)} kg CO₂e</div>
          <span className="text-[11px] font-mono text-emerald-700 mt-1.5 block">{totalPct.toFixed(1)}% {t('budgets.kpi.totalConsumption')}</span>
        </div>
        <div className="card p-4">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('budgets.kpi.forecast')}</span>
          <div className="text-2xl font-semibold font-mono text-amber-600 mt-1.5">{totalForecastKg.toFixed(2)} kg CO₂e</div>
          <span className="text-[11px] font-mono text-amber-700 mt-1.5 block">
            {totalForecastKg > totalQuotaKg
              ? t('budgets.kpi.overrun', { amount: (totalForecastKg - totalQuotaKg).toFixed(2) })
              : t('budgets.kpi.underQuota', { amount: Math.max(0, totalQuotaKg - totalForecastKg).toFixed(2) })}
          </span>
        </div>
      </div>

      {/* Team Quota Table */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">{t('budgets.tableTitle')}</h2>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">{t('budgets.alertsInfo')}</span>
        </div>
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
                    row.status === 'BREACHED' ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200' :
                    row.status === 'CRITICAL' || row.status === 'WARNING' ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-200' :
                    'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-200'
                  }`}>
                    {t(`budgets.status.${row.status.toLowerCase()}`)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pre-Deploy PR Budget Gate Check */}
      <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-emerald-400">{t('budgets.simulator.title')}</h3>
        <p className="text-xs text-slate-400 mt-1">
          {t('budgets.simulator.description')}
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 items-end">
          <div>
  <label className="text-xs text-slate-300 font-medium block mb-1">{t('budgets.simulator.targetTeam')}</label>
            <select
              value={selectedSimTeam}
              onChange={(e) => setSelectedSimTeam(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none"
            >
              {teamBudgets.map((b) => (
                <option key={b.team} value={b.team}>
                  {b.team} ({b.consumedKg.toFixed(1)} / {b.limitKg.toFixed(0)} kg used)
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">{t('budgets.simulator.projectedEmission')}</label>
            <input
              type="number"
              step="1"
              min="0"
              value={prEmissionsInput}
              onChange={(e) => setPrEmissionsInput(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none"
            />
          </div>
          <div className="p-3 rounded-lg bg-slate-800 border border-slate-700">
            <span className="text-xs text-slate-400 block font-medium">
              {t('budgets.simulator.mergeGateVerdict', { pct: simResult?.projectedPct.toFixed(1) || '' })}
            </span>
            <span
              className={`text-sm font-bold ${
                simResult?.verdict === 'BLOCKED'
                  ? 'text-red-400'
                  : simResult?.verdict === 'WARNING'
                  ? 'text-amber-400'
                  : 'text-emerald-400'
              }`}
            >
              {simResult
                ? `${simResult.verdict} - ${simResult.reason}`
                : t('budgets.simulator.evaluating')}
            </span>
          </div>
        </div>
      </div>

    </div>
  );
}



