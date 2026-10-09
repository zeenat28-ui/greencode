import React, { useState } from 'react';
import { 
  Building2, Users, ShieldAlert, CheckCircle2, TrendingDown,
  DollarSign, Activity, GitPullRequest, ArrowUpRight
} from 'lucide-react';

export default function Overview() {
  const [selectedOrg] = useState('Acme Corporation (Enterprise)');
  const [selectedTeam, setSelectedTeam] = useState('All Teams');

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 text-white shadow-xl flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              ● Multi-Tenant Isolated
            </span>
            <span className="text-slate-400 text-xs">Org ID: 1</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight">{selectedOrg}</h1>
          <p className="text-slate-400 text-sm mt-1">Enterprise Software Energy & Carbon Control Plane</p>
        </div>
        <div className="flex items-center gap-3">
          <select 
            value={selectedTeam} 
            onChange={(e) => setSelectedTeam(e.target.value)}
            className="bg-slate-800 border border-slate-700 text-slate-200 text-sm rounded-lg px-3 py-2 outline-none focus:border-emerald-500"
          >
            <option>All Teams</option>
            <option>Core Infra</option>
            <option>Payments Team</option>
            <option>Commerce Service</option>
          </select>
          <button className="bg-emerald-500 hover:bg-emerald-400 text-slate-950 font-semibold px-4 py-2 rounded-lg text-sm transition-all shadow-lg shadow-emerald-500/20">
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
          <div className="text-2xl font-bold text-slate-900 mt-2">320.4 / 500 kg</div>
          <div className="mt-3">
            <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
              <div className="h-full bg-emerald-500 rounded-full" style={{ width: '64%' }}></div>
            </div>
            <div className="flex justify-between text-xs text-slate-500 mt-1.5 font-medium">
              <span>64% Consumed</span>
              <span>179.6 kg remaining</span>
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
            <span>K8s Sentinel Protection</span>
            <Activity className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">12 / 12 Pods</div>
          <p className="text-xs text-emerald-600 mt-3 font-medium flex items-center gap-1">
            <span>● Live Rollback Armed (&gt;35% spike)</span>
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <div className="flex justify-between items-start text-slate-500 text-xs font-medium uppercase tracking-wider">
            <span>Annual Cloud Savings</span>
            <DollarSign className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-slate-900 mt-2">$18,420 / yr</div>
          <p className="text-xs text-slate-500 mt-3 font-medium flex items-center gap-1">
            <TrendingDown className="w-3.5 h-3.5 text-emerald-600" />
            <span>-14.2 tCO2e Scope 2 avoided</span>
          </p>
        </div>
      </div>

      {/* Monitored Projects Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900 text-base">Monitored Enterprise Repositories & Services</h2>
          <span className="text-xs text-slate-500 font-medium">Auto-scanned via GitHub Actions CI/CD</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
              <tr>
                <th className="px-5 py-3.5 font-medium">Service / Repository</th>
                <th className="px-5 py-3.5 font-medium">Team</th>
                <th className="px-5 py-3.5 font-medium">Green Score</th>
                <th className="px-5 py-3.5 font-medium">PR Gate Policy</th>
                <th className="px-5 py-3.5 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-4 font-semibold text-slate-900">acme/payments-api</td>
                <td className="px-5 py-4 text-slate-600">Payments Team</td>
                <td className="px-5 py-4 text-emerald-600 font-bold">96.4 / 100</td>
                <td className="px-5 py-4 text-slate-600">Max +15% Regression</td>
                <td className="px-5 py-4"><span className="px-2.5 py-1 text-xs rounded-full bg-emerald-50 text-emerald-700 font-medium">COMPLIANT</span></td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-4 font-semibold text-slate-900">acme/search-service</td>
                <td className="px-5 py-4 text-slate-600">Core Infra</td>
                <td className="px-5 py-4 text-emerald-600 font-bold">91.2 / 100</td>
                <td className="px-5 py-4 text-slate-600">Max +20% Regression</td>
                <td className="px-5 py-4"><span className="px-2.5 py-1 text-xs rounded-full bg-emerald-50 text-emerald-700 font-medium">COMPLIANT</span></td>
              </tr>
              <tr className="hover:bg-slate-50/50">
                <td className="px-5 py-4 font-semibold text-slate-900">acme/checkout-flow</td>
                <td className="px-5 py-4 text-slate-600">Commerce Service</td>
                <td className="px-5 py-4 text-amber-600 font-bold">78.5 / 100</td>
                <td className="px-5 py-4 text-slate-600">Max +10% Regression</td>
                <td className="px-5 py-4"><span className="px-2.5 py-1 text-xs rounded-full bg-amber-50 text-amber-700 font-medium">WARNING</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
