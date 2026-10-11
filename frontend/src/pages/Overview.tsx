import React, { useState, useEffect, useCallback } from 'react';
import {
  Building2, CheckCircle2, TrendingDown,
  DollarSign, Activity, GitPullRequest, RefreshCw
} from 'lucide-react';

export default function Overview() {
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
    fetch('/api/repositories?limit=15')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.repositories)) {
          setLiveRepos(data.repositories);
        }
      })
      .catch(() => {});

    fetch('/api/energy/budgets')
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

    fetch('/api/energy/workloads?limit=12')
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

    const token = localStorage.getItem('greencode_token');
    if (token) {
      fetch('/api/enterprise/organizations/me', {
        headers: { Authorization: `Bearer ${token}` },
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
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subpath: 'app',
          repo_name: 'greencode-org/greencode',
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
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              Multi-Tenant Isolated
            </span>
            <span className="text-slate-400 text-xs">Org ID: 1</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{selectedOrg}</h1>
          <p className="text-slate-400 text-sm mt-1">Software Energy, Carbon Budget & Workload Control Plane</p>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={selectedTeam}
            onChange={(e) => setSelectedTeam(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 outline-none focus:border-emerald-500"
          >
            <option value="All Teams">All Teams</option>
            {teams.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
          <button
            onClick={handleScanLocalWorkspace}
            disabled={scanningLocal}
            className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-100 font-semibold px-3.5 py-2 rounded-lg text-sm transition-all flex items-center gap-1.5"
          >
            <RefreshCw className={`w-4 h-4 ${scanningLocal ? 'animate-spin text-emerald-400' : 'text-emerald-400'}`} />
            {scanningLocal ? 'Scanning Workspace...' : 'Scan Local Workspace'}
          </button>
          <button
            onClick={handleExportDisclosure}
            className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition-all shadow-lg shadow-emerald-500/20"
          >
            Export SEC Disclosure
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Monthly Carbon Quota</span>
            <Building2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">{quotaStats.consumed.toFixed(2)} / {quotaStats.limit.toFixed(0)} kg</div>
          <div className="mt-3">
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: `${quotaPct}%` }}></div>
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-1.5 font-medium">
              <span>{quotaPct}% Consumed</span>
              <span>{quotaRemaining.toFixed(2)} kg remaining</span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>PR Gatekeeper Verdict</span>
            <GitPullRequest className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-emerald-600 mt-2 flex items-center gap-1.5">
            <CheckCircle2 className="w-6 h-6" /> 15% Max SLA
          </div>
          <p className="text-xs text-slate-500 mt-3 font-medium">Blocking regressions before merge</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Active Runtime Workloads</span>
            <Activity className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            {workloadSummary.healthy} / {workloadSummary.total} Healthy
          </div>
          <p className="text-xs text-emerald-600 mt-3 font-medium flex items-center gap-1">
            <span>Source: {workloadSummary.source} (&gt;35% spike guard)</span>
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Monitored Runtime Power Cost</span>
            <DollarSign className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">
            ${workloadSummary.annualCostUsd.toFixed(2)} / yr
          </div>
          <p className="text-xs text-slate-500 mt-3 font-medium flex items-center gap-1">
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
            <span>{workloadSummary.annualCo2Kg.toFixed(1)} kg CO2e / yr projected</span>
          </p>
        </div>
      </div>

      {/* Monitored Projects Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900 text-base">Audited Repositories & Services ({filteredRepos.length})</h2>
          <span className="text-xs text-slate-500 font-medium">Persisted in SQLite / PostgreSQL Audit Ledger</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5 font-medium">Service / Repository</th>
                <th className="px-5 py-3.5 font-medium">Files / Lines</th>
                <th className="px-5 py-3.5 font-medium">Green Score</th>
                <th className="px-5 py-3.5 font-medium">Violations</th>
                <th className="px-5 py-3.5 font-medium">Status</th>
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
                        {repo.repo_name || repo.full_name || repo.name || 'greencode-org/greencode'}
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {Number(repo.total_files ?? 0)} files / {Number(repo.total_lines ?? 0).toLocaleString()} LOC
                      </td>
                      <td className={`px-5 py-4 font-bold ${compliant ? 'text-emerald-600' : 'text-amber-600'}`}>
                        {score.toFixed(1)} / 100
                      </td>
                      <td className="px-5 py-4 text-slate-600">
                        {violationsCount} finding{violationsCount === 1 ? '' : 's'}
                      </td>
                      <td className="px-5 py-4">
                        <span className={`px-2.5 py-1 text-xs rounded-full font-medium ${compliant ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>
                          {compliant ? 'COMPLIANT' : 'REVIEW REQUIRED'}
                        </span>
                      </td>
                    </tr>
                  );
                })
              ) : (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-500">
                    No repositories have been audited yet. Click <strong>Scan Local Workspace</strong> above to audit this codebase and populate live telemetry.
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

