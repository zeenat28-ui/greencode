import React, { useState } from 'react';
import { DollarSign, AlertTriangle, CheckCircle, TrendingUp, AlertCircle, Plus } from 'lucide-react';

export default function Budgets() {
  const [activeTab, setActiveTab] = useState<'teams' | 'calculator'>('teams');
  const [prEmissionsInput, setPrEmissionsInput] = useState<number>(25.0);

  const teamBudgets = [
    { team: 'Core Infra', limitKg: 500.0, consumedKg: 180.0, burnRate: '6.0 kg/day', status: 'NORMAL', pct: 36.0 },
    { team: 'Payments', limitKg: 250.0, consumedKg: 235.0, burnRate: '7.8 kg/day', status: 'CRITICAL', pct: 94.0 },
    { team: 'Commerce', limitKg: 300.0, consumedKg: 310.0, burnRate: '10.3 kg/day', status: 'BREACHED', pct: 103.3 },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Enterprise Carbon & Cost Budgets</h1>
          <p className="text-sm text-slate-500">Allocate monthly carbon quotas (kg CO2e) and prevent team overruns</p>
        </div>
        <button className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-1.5 transition-colors shadow-sm">
          <Plus className="w-4 h-4" /> Allocate Team Budget
        </button>
      </div>

      {/* Grid Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Total Monthly Quota</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">1,050.0 kg CO2e</div>
          <span className="text-xs text-slate-500 font-medium mt-2 block">Allocated across 3 engineering teams</span>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Current Month Consumed</span>
          <div className="text-2xl font-bold text-slate-900 mt-1">725.0 kg CO2e</div>
          <span className="text-xs text-emerald-600 font-medium mt-2 block">69.0% total tenant consumption</span>
        </div>
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Forecasted Month-End</span>
          <div className="text-2xl font-bold text-amber-600 mt-1">1,120.5 kg CO2e</div>
          <span className="text-xs text-amber-600 font-medium mt-2 block">⚠️ +70.5 kg overrun projected</span>
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
                <td className="px-5 py-4 text-slate-900 font-medium">{t.consumedKg.toFixed(1)} kg</td>
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
                    t.status === 'CRITICAL' ? 'bg-amber-50 text-amber-700' :
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
        <h3 className="text-base font-semibold text-emerald-400">⚡ Pre-Deploy PR Carbon Impact Simulator</h3>
        <p className="text-xs text-slate-400 mt-1">Simulate if an incoming pull request's projected emissions will breach your team budget</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-4 items-end">
          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Target Team</label>
            <select className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none">
              <option>Payments (+250 kg limit)</option>
              <option>Core Infra (+500 kg limit)</option>
            </select>
          </div>
          <div>
            <label className="text-xs text-slate-300 font-medium block mb-1">Projected PR Emission (kg CO2e)</label>
            <input 
              type="number" 
              value={prEmissionsInput} 
              onChange={(e) => setPrEmissionsInput(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 text-white text-sm rounded-lg p-2.5 outline-none"
            />
          </div>
          <div className="p-3 rounded-lg bg-slate-800 border border-slate-700">
            <span className="text-xs text-slate-400 block font-medium">Merge Gate Verdict</span>
            <span className={`text-sm font-bold ${prEmissionsInput > 15 ? 'text-red-400' : 'text-emerald-400'}`}>
              {prEmissionsInput > 15 ? '🔴 BLOCKED - Exceeds monthly team quota' : '🟢 APPROVED - Quota headroom available'}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

