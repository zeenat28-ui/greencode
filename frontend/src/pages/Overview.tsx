import React, { useState, useEffect, useCallback } from 'react';
import {
  Building2, CheckCircle2, TrendingDown,
  DollarSign, Activity, GitPullRequest, RefreshCw
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import { authHeaders, getAccessToken } from '../services/api';

export default function Overview() {
  const t = useT();
  const [selectedOrg, setSelectedOrg] = useState('GreenCode Organization');
  const [selectedTeam, setSelectedTeam] = useState('All Teams');
  const [liveRepos, setLiveRepos] = useState<any[]>([]);
  const [teams, setTeams] = useState<string[]>(['core-infra']);
  const [quotaStats, setQuotaStats] = useState({ consumed: 0.0, limit: 500.0 });
  const [workloadSummary, setWorkloadSummary] = useState({
    healthy: 0,
    total: 0,
    source: 'host_psutil',
    annualCostUsd: 0.0,
    annualCo2Kg: 0.0,
  });
  const [scanningLocal, setScanningLocal] = useState(false);

  const loadOverviewData = useCallback(() => {
    fetch('/api/repositories?limit=15', { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.repositories)) {
          setLiveRepos(data.repositories);
        }
      })
      .catch(() => {});

    fetch('/api/energy/budgets', { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.budgets) && data.budgets.length > 0) {
          const limit = data.budgets.reduce((s: number, b: any) => s + Number(b.monthly_budget_kg ?? 0), 0);
          const consumed = data.budgets.reduce((s: number, b: any) => s + Number(b.current_consumed_kg ?? 0), 0);
          const discoveredTeams = data.budgets
            .map((b: any) => String(b.team_id || '').trim())
            .filter(Boolean);
          if (discoveredTeams.length > 0) {
            setTeams(discoveredTeams);
          }
          if (limit > 0) {
            setQuotaStats({ consumed, limit });
          }
        }
      })
      .catch(() => {});

    fetch('/api/energy/workloads?limit=12', { headers: authHeaders() })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && typeof data === 'object') {
          setWorkloadSummary({
            healthy: Number(data.healthy_workloads ?? 0),
            total: Number(data.total_workloads ?? 0),
            source: String(data.telemetry_source || 'host_psutil'),
            annualCostUsd: Number(data.total_annual_cost_usd ?? 0),
            annualCo2Kg: Number(data.total_annual_co2_kg ?? 0),
          });
        }
      })
      .catch(() => {});

    // The access token lives in memory only (never in localStorage), so ask
    // the API layer whether there is a session before hitting a protected route.
    if (getAccessToken()) {
      fetch('/api/enterprise/organizations/me', {
        headers: authHeaders(),
      })
        .then((r) => (r.ok ? r.json() : null))
        .then((data) => {
          if (data?.organization?.name) {
            setSelectedOrg(String(data.organization.name));
          }
        })
        .catch(() => {});
    }
  }, []);

  useEffect(() => {
    loadOverviewData();
  }, [loadOverviewData]);

  const handleScanLocalWorkspace = async () => {
    setScanningLocal(true);
    try {
      const targetTeam = selectedTeam === 'All Teams' ? (teams[0] || 'core-infra') : selectedTeam;
      await fetch('/api/scan/local-workspace', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          subpath: 'app',
          repo_name: 'zeenat28-ui/greencode',
          team_id: targetTeam,
        }),
      });
      loadOverviewData();
    } catch {
      // Best-effort refresh
    } finally {
      setScanningLocal(false);
    }
  };

  const quotaPct = Math.min(100, Math.round((quotaStats.consumed / Math.max(1, quotaStats.limit)) * 100));
  const quotaRemaining = Math.max(0, quotaStats.limit - quotaStats.consumed);

  const handleExportDisclosure = () => {
    window.open('/api/reports/esg/1', '_blank', 'noopener,noreferrer');
  };

  const filteredRepos = liveRepos.filter((repo) => {
    if (selectedTeam === 'All Teams') return true;
    const repoTeam = String(repo.team_id || 'core-infra');
    return repoTeam.toLowerCase() === selectedTeam.toLowerCase();
  });

  return (
    <div className="space-y-5">
      {/* Top Banner */}
      <div className="bg-zinc-950 border border-zinc-800 rounded-xl p-5 text-white shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
             <span className="px-2 py-0.5 rounded-md text-[11px] font-mono font-medium bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
               {t('overview.tenantIsolated')}
             </span>
            <span className="text-zinc-400 text-xs font-mono">org_id: 1</span>
          </div>
          <h1 className="text-lg font-semibold tracking-tight text-zinc-100">{selectedOrg}</h1>
           <p className="text-zinc-400 text-xs mt-0.5">{t('overview.orgSubtitle')}</p>
        </div>
        <div className="flex flex-wrap items-center gap-2.5">
          <select
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            className="bg-zinc-900 border border-zinc-700 text-zinc-200 text-xs font-mono rounded-lg px-3 py-2 outline-none focus:border-emerald-500"
          >
            <option value="All Teams">{t('overview.allTeams')}</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={handleScanLocalWorkspace}
            disabled={scanningLocal}
            className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-100 font-medium px-3 py-2 rounded-lg text-xs transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${scanningLocal ? 'animate-spin text-emerald-400' : 'text-emerald-400'}`} />
             {scanningLocal ? t('overview.scanWorkspace') : t('overview.auditWorkspace')}
          </button>
          <button
            onClick={handleExportDisclosure}
            className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-3.5 py-2 rounded-lg text-xs transition-all shadow-sm"
          >
             {t('overview.exportEsgJson')}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-4">
          <div className="flex justify-between items-start text-zinc-500 text-xs font-medium">
             <span>{t('overview.carbonQuota')}</span>
             <Building2 className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-semibold font-mono text-zinc-950 mt-2">{quotaStats.consumed.toFixed(2)} / {quotaStats.limit.toFixed(0)} kg</div>
          <div className="mt-2.5">
            <div className="h-1.5 w-full bg-zinc-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-600 rounded-full" style={{ width: `${quotaPct}%` }}></div>
            </div>
            <div className="flex justify-between text-[11px] font-mono text-zinc-500 mt-1.5">
               <span>{t('overview.quotaPct', { pct: String(quotaPct) })}</span>
               <span>{t('overview.quotaFree', { kg: quotaRemaining.toFixed(1) })}</span>
            </div>
          </div>
        </div>

        <div className="card p-4">
          <div className="flex justify-between items-start text-zinc-500 text-xs font-medium">
             <span>{t('overview.prSlaTitle')}</span>
             <GitPullRequest className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-semibold font-mono text-emerald-600 mt-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-5 h-5" /> &le; 15% Δ
          </div>
           <p className="text-[11px] text-zinc-500 mt-2">{t('overview.prSlaDesc')}</p>
        </div>

        <div className="card p-4">
          <div className="flex justify-between items-start text-zinc-500 text-xs font-medium">
             <span>{t('overview.runtimeWorkloads')}</span>
             <Activity className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-semibold font-mono text-zinc-950 mt-2">
            {t('overview.healthyCount', { healthy: String(workloadSummary.healthy), total: String(workloadSummary.total) })}
          </div>
            <p className="text-[11px] font-mono text-emerald-700 mt-2">
             {t('overview.sourceLabel', { source: workloadSummary.source })}
            </p>
        </div>

        <div className="card p-4">
          <div className="flex justify-between items-start text-zinc-500 text-xs font-medium">
             <span>{t('overview.runtimeDraw')}</span>
             <DollarSign className="w-4 h-4 text-zinc-400" />
          </div>
          <div className="text-2xl font-semibold font-mono text-zinc-950 mt-2">
            {t('overview.annualCost', { cost: workloadSummary.annualCostUsd.toFixed(2) })}
          </div>
          <p className="text-[11px] font-mono text-zinc-500 mt-2 flex items-center gap-1">
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
             <span>{t('overview.co2Yearly', { co2: workloadSummary.annualCo2Kg.toFixed(1) })}</span>
          </p>
        </div>
      </div>

      {/* Monitored Projects Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
           <h2 className="font-semibold text-slate-900 text-base">{t('overview.pageTitle', { count: String(filteredRepos.length) })}</h2>
           <span className="text-xs text-slate-500 font-medium">{t('overview.ledgerHint')}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
               <tr>
                 <th className="px-5 py-3.5 font-medium">{t('overview.colServiceName')}</th>
                 <th className="px-5 py-3.5 font-medium">{t('overview.colFiles')}</th>
                 <th className="px-5 py-3.5 font-medium">{t('overview.colGreenScore')}</th>
                 <th className="px-5 py-3.5 font-medium">{t('overview.colViolations')}</th>
                 <th className="px-5 py-3.5 font-medium">{t('overview.colStatusLabel')}</th>
               </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filteredRepos.length > 0 ? (
                filteredRepos.map((repo, idx) => {
                  const score = Number(repo.green_score ?? 100);
                  const compliant = score >= 75;
                  const violationsCount = Number(repo.total_violations ?? 0);
                  return (
                    <tr key={repo.id || idx} className="hover:bg-slate-50/50">
                      <td className="px-5 py-4 font-semibold text-slate-900">
                        {repo.repo_name || repo.full_name || repo.name || 'zeenat28-ui/greencode'}
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {Number(repo.total_files ?? 0)} files / {Number(repo.total_lines ?? 0).toLocaleString()} LOC
                      </td>
                      <td className={`px-5 py-4 font-bold ${compliant ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {score.toFixed(1)} / 100
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {t('overview.findingsCount', { count: String(violationsCount), plural: violationsCount === 1 ? '' : 's' })}
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${compliant ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                          {compliant ? t('overview.statusCompliant') : t('overview.statusReview')}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                   <td colSpan={5} className="px-5 py-8 text-center text-slate-500">
                     <span dangerouslySetInnerHTML={{ __html: t('overview.emptyBody') }} />
                   </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

