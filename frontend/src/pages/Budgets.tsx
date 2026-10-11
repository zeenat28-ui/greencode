import React, { useState, useEffect, useCallback } from 'react';
import { Plus, CheckCircle2 } from 'lucide-react';

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
  const [focusReport, setFocusReport] = useState<any>(null);

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
        burnRate: `${dailyBurnKg.toFixed(2)} kg/day`,
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

    fetch('/api/billing/focus/sample-report')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.reconciled_items)) {
          setFocusReport(data);
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
        setAllocationMsg(`Allocated ${newTeamQuotaKg.toFixed(1)} kg CO2e monthly quota for team '${cleanTeam}'.`);
      }
    } catch {
      setAllocationMsg(`Could not persist budget allocation for '${cleanTeam}'.`);
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
    <div className="space-y-6">
      {/* Header & Allocation Form */}
      <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Team Carbon & Cost Budgets</h1>
            <p className="text-sm text-slate-500">Allocate monthly carbon quotas (kg CO2e) and enforce pre-merge budget gates</p>
          </div>
        </div>

        <form onSubmit={handleAllocateBudget} className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-2 border-t border-slate-100 items-end">
          <div>
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Team Identifier
            </label>
            <input
              type="text"
              value={newTeamName}
              onChange={(e) => setNewTeamName(e.target.value)}
              placeholder="e.g. core-infra, payments, ml-platform"
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
          </div>
          <div>
            <label className="text-xs font-semibold text-slate-600 uppercase tracking-wider block mb-1">
              Monthly Carbon Quota (kg CO2e)
            </label>
            <input
              type="number"
              step="10"
              min="1"
              value={newTeamQuotaKg}
              onChange={(e) => setNewTeamQuotaKg(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
          </div>
          <button
            type="submit"
            disabled={allocating}
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2.5 rounded-lg text-sm flex items-center justify-center gap-1.5 transition-colors shadow-sm"
          >
            <Plus className="w-4 h-4" />
            {allocating ? 'Saving Quota...' : 'Allocate / Update Team Budget'}
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
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Monthly Quota</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalQuotaKg.toFixed(1)} kg CO2e</div>
          <span className="text-xs text-slate-500 font-medium mt-2 block">Allocated across {teamBudgets.length} engineering team(s)</span>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current Month Consumed</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">{totalConsumedKg.toFixed(2)} kg CO2e</div>
          <span className="text-xs text-emerald-600 font-medium mt-2 block">{totalPct.toFixed(1)}% total tenant consumption</span>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Forecasted Month-End</span>
          <div className="text-2xl font-bold text-amber-600 mt-1">{totalForecastKg.toFixed(2)} kg CO2e</div>
          <span className="text-xs text-amber-600 font-medium mt-2 block">
            {totalForecastKg > totalQuotaKg
              ? `+${(totalForecastKg - totalQuotaKg).toFixed(2)} kg overrun projected`
              : `${Math.max(0, totalQuotaKg - totalForecastKg).toFixed(2)} kg under quota projected`}
          </span>
        </div>
      </div>

      {/* Team Quota Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900">Active Team Quotas & Burn Velocity</h2>
          <span className="text-xs text-slate-500 font-medium">Alerts at 70% (Warning), 90% (Critical), 100% (Breached)</span>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5">Team Name</th>
              <th className="px-5 py-3.5">Monthly Quota</th>
              <th className="px-5 py-3.5">Consumed</th>
              <th className="px-5 py-3.5">Daily Burn</th>
              <th className="px-5 py-3.5">Quota Meter</th>
              <th className="px-5 py-3.5">Alert Level</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {teamBudgets.map((t) => (
              <tr key={t.team} className="hover:bg-slate-50/50">
                <td className="px-5 py-4 font-semibold text-slate-900">{t.team}</td>
                <td className="px-5 py-4 text-slate-600">{t.limitKg.toFixed(1)} kg</td>
                <td className="px-5 py-4 text-slate-900 font-medium">{t.consumedKg.toFixed(2)} kg</td>
                <td className="px-5 py-4 text-slate-500">{t.burnRate}</td>
                <td className="px-5 py-4 w-48">
                  <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${t.pct >= 100 ? 'bg-red-500' : t.pct >= 90 ? 'bg-amber-500' : 'bg-emerald-500'}`}
                      style={{ width: `${Math.min(100, t.pct)}%` }}
                    />
                  </div>
                  <span className="text-xs text-slate-500 mt-1 block">{t.pct.toFixed(1)}%</span>
                </td>
                <td className="px-5 py-4">
                  <span className={`px-2.5 py-1 text-xs rounded-full font-semibold ${
                    t.status === 'BREACHED' ? 'bg-red-50 text-red-700' :
                    t.status === 'CRITICAL' || t.status === 'WARNING' ? 'bg-amber-50 text-amber-700' :
                    'bg-emerald-50 text-emerald-700'
                  }`}>
                    {t.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pre-Deploy PR Budget Gate Check */}
      <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-6 shadow-sm">
        <h3 className="text-base font-semibold text-emerald-400">Pre-Deploy PR Carbon Impact Simulator</h3>
        <p className="text-xs text-slate-400 mt-1">
          Evaluate whether an incoming pull request's projected emissions will breach the selected team's remaining monthly carbon quota
        </p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 items-end">
          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Target Team</label>
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
            <label className="text-xs text-slate-300 font-medium block mb-1">Projected PR Emission (kg CO2e)</label>
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
              Merge Gate Verdict {simResult ? `(${simResult.projectedPct.toFixed(1)}% of quota)` : ''}
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
                : 'Evaluating against team quota...'}
            </span>
          </div>
        </div>
      </div>

      {/* FinOps Foundation FOCUS 1.4 Cloud Billing & Carbon Reconciliation */}
      {focusReport && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-200 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div>
              <h2 className="font-semibold text-slate-900">FinOps Foundation FOCUS 1.4 Cloud Billing &amp; Carbon Reconciliation</h2>
              <p className="text-xs text-slate-500">
                Reconciles BilledCost and EffectiveCost against regional PUE, grid intensity (gCO2e/kWh), and AWS Graviton right-sizing
              </p>
            </div>
            <div className="flex gap-2 text-xs font-semibold">
              <span className="px-2.5 py-1 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                Savings: ${focusReport.summary?.identified_monthly_usd_savings}/mo (${focusReport.summary?.identified_annual_usd_savings}/yr)
              </span>
              <span className="px-2.5 py-1 rounded-full bg-blue-50 text-blue-700 border border-blue-200">
                Avoidable: {focusReport.summary?.identified_co2e_savings_kg} kg CO2e/mo
              </span>
            </div>
          </div>
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
              <tr>
                <th className="px-5 py-3">Service / Resource</th>
                <th className="px-5 py-3">SKU</th>
                <th className="px-5 py-3">Region (Grid)</th>
                <th className="px-5 py-3">EffectiveCost</th>
                <th className="px-5 py-3">Energy &amp; Carbon</th>
                <th className="px-5 py-3">Potential Savings</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {(focusReport.reconciled_items || []).map((item: any, idx: number) => (
                <tr key={idx} className="hover:bg-slate-50/50">
                  <td className="px-5 py-3.5">
                    <div className="font-semibold text-slate-900">{item.service_name}</div>
                    <div className="text-xs font-mono text-slate-400">{item.resource_id}</div>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-xs text-slate-800">{item.resource_type}</td>
                  <td className="px-5 py-3.5 text-xs text-slate-600">
                    {item.region_id} ({item.grid_intensity_gco2_kwh} gCO2/kWh)
                  </td>
                  <td className="px-5 py-3.5 font-mono font-semibold text-slate-900">
                    ${Number(item.effective_cost_usd).toFixed(2)}
                  </td>
                  <td className="px-5 py-3.5 text-xs text-slate-700 font-mono">
                    {item.estimated_energy_kwh} kWh &middot; {item.total_co2e_kg} kg CO2e
                  </td>
                  <td className="px-5 py-3.5">
                    {item.potential_monthly_usd_savings > 0 ? (
                      <span className="text-xs font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-1 rounded-full">
                        -${item.potential_monthly_usd_savings}/mo (-{item.potential_co2e_savings_kg} kg CO2e)
                      </span>
                    ) : (
                      <span className="text-xs text-slate-400">Optimal Graviton / Clean Grid</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}



