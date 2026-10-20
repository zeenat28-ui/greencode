import React, { useState, useEffect, useCallback } from 'react';
import { RotateCcw, AlertTriangle, RefreshCw, Sliders } from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import { authHeaders } from '../services/api';

interface LiveWorkload {
  name: string;
  namespace: string;
  container_name: string;
  current_power_w: number;
  baseline_power_w: number;
  spike_pct: number;
  spike: string;
  cpu_millicores: number;
  memory_mb: number;
  annual_cost_usd: number;
  annual_co2_kg: number;
  status: string;
  telemetry_source: string;
}

export default function Deployments() {
  const t = useT();
  const [workloads, setWorkloads] = useState<LiveWorkload[]>([]);
  const [telemetrySource, setTelemetrySource] = useState<string>('host_psutil');
  const [loading, setLoading] = useState<boolean>(true);
  const [rollbackStatus, setRollbackStatus] = useState<string | null>(null);
  const [triggering, setTriggering] = useState(false);

  const [selectedWorkload, setSelectedWorkload] = useState<string>('');
  const [selectedNamespace, setSelectedNamespace] = useState<string>('host-runtime');
  const [baselineInputW, setBaselineInputW] = useState<number>(10.0);

  const fetchWorkloads = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/energy/workloads?limit=12', { headers: authHeaders() });
      if (res.ok) {
        const data = await res.json();
        const items: LiveWorkload[] = Array.isArray(data.workloads) ? data.workloads : [];
        setWorkloads(items);
        setTelemetrySource(String(data.telemetry_source || 'host_psutil'));
        if (items.length > 0 && !selectedWorkload) {
          setSelectedWorkload(items[0].name);
          setSelectedNamespace(items[0].namespace);
          setBaselineInputW(items[0].baseline_power_w);
        }
      }
    } catch {
      // Retain existing list on transient error
    } finally {
      setLoading(false);
    }
  }, [selectedWorkload]);

  useEffect(() => {
    fetchWorkloads();
  }, [fetchWorkloads]);

  const handleManualRollback = async (w: LiveWorkload) => {
    setTriggering(true);
    try {
      const res = await fetch('/api/energy/rollback', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          namespace: w.namespace,
          deployment_name: w.name,
          current_power_w: w.current_power_w,
          baseline_power_w: w.baseline_power_w,
          auto_trigger: true,
        }),
      });
      const data = await res.json();
      const mode = data?.rollback_status?.execution_mode || 'evaluated';
      setRollbackStatus(
        t('deployments.rollbackSentinel', { ns: w.namespace, name: w.name, verdict: data.verdict, pct: data.spike_pct, mode })
      );
    } catch {
      setRollbackStatus(t('deployments.emergencyRollback', { ns: w.namespace, name: w.name }));
    } finally {
      setTriggering(false);
    }
  };

  const handleUpdateBaseline = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedWorkload || baselineInputW <= 0) return;
    try {
      await fetch('/api/energy/workloads/baseline', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          namespace: selectedNamespace,
          deployment_name: selectedWorkload,
          baseline_power_w: baselineInputW,
        }),
      });
      setRollbackStatus(t('deployments.baselineRegistered', { w: baselineInputW.toFixed(2), ns: selectedNamespace, name: selectedWorkload }));
      fetchWorkloads();
    } catch {
      setRollbackStatus(t('deployments.couldNotUpdate', { name: selectedWorkload }));
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-zinc-200/80 dark:border-slate-700 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 tracking-tight">{t('deployments.title')}</h1>
            <span className="badge-olive">
              source: {telemetrySource}
            </span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            {t('deployments.subtitle')}
          </p>
        </div>
        <button
          onClick={fetchWorkloads}
          disabled={loading}
          className="btn-primary text-xs px-3.5 py-2 flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          {loading ? t('deployments.sampling') : t('deployments.refreshButton')}
        </button>
      </div>

      {rollbackStatus && (
        <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 text-amber-900 dark:text-amber-200 text-sm p-4 rounded-xl flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <span>{rollbackStatus}</span>
          </div>
        </div>
      )}

      {/* Baseline Calibration Bar */}
      <form
        onSubmit={handleUpdateBaseline}
        className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm grid grid-cols-1 md:grid-cols-4 gap-4 items-end"
      >
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider block mb-1">
            {t('deployments.targetWorkload')}
          </label>
          <select
            value={selectedWorkload}
            onChange={(e) => {
              const name = e.target.value;
              setSelectedWorkload(name);
              const found = workloads.find((w) => w.name === name);
              if (found) {
                setSelectedNamespace(found.namespace);
                setBaselineInputW(found.baseline_power_w);
              }
            }}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-900 dark:text-slate-100 outline-none"
          >
            {workloads.map((w) => (
              <option key={`${w.namespace}/${w.name}`} value={w.name}>
                {w.name} ({w.current_power_w.toFixed(2)} W {t('deployments.observed')})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider block mb-1">
            {t('deployments.runtimeNamespace')}
          </label>
          <input
            type="text"
            value={selectedNamespace}
            onChange={(e) => setSelectedNamespace(e.target.value)}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-900 dark:text-slate-100 outline-none"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider block mb-1">
            {t('deployments.baselineWatts')}
          </label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            value={baselineInputW}
            onChange={(e) => setBaselineInputW(Number(e.target.value))}
            className="w-full bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg p-2.5 text-sm text-slate-900 dark:text-slate-100 outline-none"
          />
        </div>
        <button
          type="submit"
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2.5 rounded-lg text-sm flex items-center justify-center gap-1.5 transition-colors"
        >
          <Sliders className="w-4 h-4" /> {t('deployments.setBaseline')}
        </button>
      </form>

      {/* Workloads List */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex justify-between items-center">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100">{t('deployments.activeWorkloads', { count: workloads.length })}</h2>
          <span className="text-xs text-slate-500 dark:text-slate-400 font-medium">{t('deployments.rollbackWarning')}</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs uppercase border-b border-slate-200 dark:border-slate-700">
              <tr>
                <th className="px-5 py-3.5">{t('deployments.table.workloadName')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.namespace')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.cpuMem')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.observedPower')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.baselinePower')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.spike')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.status')}</th>
                <th className="px-5 py-3.5">{t('deployments.table.action')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {workloads.map((d) => (
                <tr key={`${d.namespace}/${d.name}`} className="hover:bg-slate-50/50 dark:hover:bg-slate-800/50">
                  <td className="px-5 py-4 font-semibold text-slate-900 dark:text-slate-100">{d.name}</td>
                  <td className="px-5 py-4 text-slate-600 dark:text-slate-400">{d.namespace}</td>
                  <td className="px-5 py-4 text-slate-600 dark:text-slate-400 font-mono text-xs">
                    {d.cpu_millicores.toFixed(0)}m / {d.memory_mb.toFixed(1)} MB
                  </td>
                  <td className="px-5 py-4 font-medium text-slate-900 dark:text-slate-200">{d.current_power_w.toFixed(2)} W</td>
                  <td className="px-5 py-4 text-slate-500 dark:text-slate-400">{d.baseline_power_w.toFixed(2)} W</td>
                  <td
                    className="px-5 py-4 font-bold"
                    style={{
                      color:
                        d.status === 'CRITICAL_SPIKE'
                          ? '#ef4444'
                          : d.status === 'WARNING_REGRESSION'
                          ? '#f59e0b'
                          : '#10b981',
                    }}
                  >
                    {d.spike}
                  </td>
                  <td className="px-5 py-4">
                    <span
                      className={`px-2.5 py-1 text-xs rounded-full font-semibold ${
                        d.status === 'CRITICAL_SPIKE'
                          ? 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-200'
                          : d.status === 'WARNING_REGRESSION'
                          ? 'bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-200'
                          : 'bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-200'
                      }`}
                    >
                      {d.status}
                    </span>
                  </td>
                  <td className="px-5 py-4">
                    <button
                      onClick={() => handleManualRollback(d)}
                      disabled={triggering}
                      className={`${
                        d.status === 'CRITICAL_SPIKE'
                          ? 'bg-red-600 hover:bg-red-700 text-white'
                          : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-300'
                      } font-medium px-3 py-1.5 rounded-lg text-xs flex items-center gap-1 transition-colors`}
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                      {d.status === 'CRITICAL_SPIKE' ? t('deployments.rollbackNow') : t('deployments.evaluateGate')}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}


