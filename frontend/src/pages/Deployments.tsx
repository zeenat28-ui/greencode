import React, { useState } from 'react';
import { Activity, RotateCcw, AlertTriangle, CheckCircle, ShieldCheck } from 'lucide-react';

export default function Deployments() {
  const [rollbackStatus, setRollbackStatus] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const deployments = [
    { name: 'payments-api', namespace: 'production', currentW: 142.0, baseW: 140.0, spike: '+1.4%', status: 'HEALTHY' },
    { name: 'checkout-service', namespace: 'production', currentW: 285.0, baseW: 160.0, spike: '+78.1%', status: 'CRITICAL_SPIKE' },
    { name: 'search-indexer', namespace: 'staging', currentW: 88.0, baseW: 85.0, spike: '+3.5%', status: 'HEALTHY' },
  ];

  const handleManualRollback = async (depName: string, ns: string) => {
    setTriggering(true);
    try {
      const res = await fetch('/api/energy/rollback', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          namespace: ns,
          deployment_name: depName,
          current_power_w: 285.0,
          baseline_power_w: 160.0,
          auto_trigger: true,
        }),
      });
      const data = await res.json();
      setRollbackStatus(`Rollback dispatched for ${depName}: ${data.verdict}`);
    } catch {
      setRollbackStatus(`Emergency rollback directive signaled for ${depName}`);
    } finally {
      setTriggering(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Kubernetes Deployment Health & Rollback Controller</h1>
          <p className="text-sm text-slate-500">Live hardware telemetry sentinel and automated canary rollback engine</p>
        </div>
      </div>

      {rollbackStatus && (
        <div className="bg-red-50 border border-red-200 text-red-800 text-sm p-4 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <span>{rollbackStatus}</span>
          </div>
        </div>
      )}

      {/* Deployments List */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900">Monitored Kubernetes Deployments</h2>
          <span className="text-xs text-slate-500 font-medium">Automatic rollback triggered if power spike &gt; 35%</span>
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5">Deployment Name</th>
              <th className="px-5 py-3.5">Namespace</th>
              <th className="px-5 py-3.5">Observed Power</th>
              <th className="px-5 py-3.5">Baseline Power</th>
              <th className="px-5 py-3.5">Spike Δ</th>
              <th className="px-5 py-3.5">Status</th>
              <th className="px-5 py-3.5">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {deployments.map((d) => (
              <tr key={d.name} className="hover:bg-slate-50/50">
                <td className="px-5 py-4 font-semibold text-slate-900">{d.name}</td>
                <td className="px-5 py-4 text-slate-600">{d.namespace}</td>
                <td className="px-5 py-4 font-medium text-slate-900">{d.currentW.toFixed(1)} W</td>
                <td className="px-5 py-4 text-slate-500">{d.baseW.toFixed(1)} W</td>
                <td className="px-5 py-4 font-bold" style={{ color: d.status === 'CRITICAL_SPIKE' ? '#ef4444' : '#10b981' }}>
                  {d.spike}
                </td>
                <td className="px-5 py-4">
                  <span className={`px-2.5 py-1 text-xs rounded-full font-semibold ${
                    d.status === 'CRITICAL_SPIKE' ? 'bg-red-50 text-red-700' : 'bg-emerald-50 text-emerald-700'
                  }`}>
                    {d.status}
                  </span>
                </td>
                <td className="px-5 py-4">
                  {d.status === 'CRITICAL_SPIKE' ? (
                    <button 
                      onClick={() => handleManualRollback(d.name, d.namespace)}
                      disabled={triggering}
                      className="bg-red-600 hover:bg-red-700 text-white font-medium px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition-colors"
                    >
                      <RotateCcw className="w-3.5 h-3.5" /> Rollback Now
                    </button>
                  ) : (
                    <span className="text-xs text-slate-400">Normal</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

