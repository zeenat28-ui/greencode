import { useEffect, useRef, useState } from 'react';
import { profilerService, gridService } from '../services/greencodeApi';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { ScanResult, BenchmarkScript, ProfilingResult } from '../types';
import ScoreBadge from '../components/common/ScoreBadge';
import MetricCard from '../components/common/MetricCard';
import { Play, Cpu, MemoryStick, Zap, Leaf, Download, Copy, CheckCircle2, AlertCircle, Terminal, Clock, Loader2 } from 'lucide-react';

/**
 * Runtime Profiler
 * ----------------
 * In GitHub-only mode there is no local folder to profile, so this page runs a
 * fixed set of bundled benchmark scripts. The API enforces the same whitelist
 * server-side, which is what keeps `/api/profile` from becoming an
 * arbitrary-file-execution primitive.
 */
export default function Profiler() {
  const [scanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [threshold] = useLocalStorage('greencode_threshold', 75);

  const [benchmarks, setBenchmarks] = useState<BenchmarkScript[]>([]);
  const [benchmarksLoading, setBenchmarksLoading] = useState(true);
  const [selected, setSelected] = useState<string>('');

  const [gridIntensity, setGridIntensity] = useState(215);
  const [timeoutSec, setTimeoutSec] = useState(20);
  const [isProfiling, setIsProfiling] = useState(false);
  const [result, setResult] = useState<ProfilingResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [exported, setExported] = useState<string | null>(null);
  const outputRef = useRef<HTMLPreElement>(null);

  useEffect(() => {
    profilerService
      .listBenchmarks()
      .then((res) => {
        const list = res.data.benchmarks || [];
        setBenchmarks(list);
        if (list.length) setSelected(list[0].id);
      })
      .catch(() => setBenchmarks([]))
      .finally(() => setBenchmarksLoading(false));
  }, []);

  useEffect(() => {
    gridService
      .getZoneIntensity(zone)
      .then((r) => setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? 215))
      .catch(() => setGridIntensity(215));
  }, [zone]);

  const handleProfile = async () => {
    if (!selected) return;
    setIsProfiling(true);
    setError(null);
    setResult(null);
    try {
      const res = await profilerService.profile(selected, timeoutSec, zone, scanData?.repo_id);
      setResult(res.data);
    } catch (err: any) {
      setError(err?.response?.data?.detail || err?.message || 'Profiling failed.');
    } finally {
      setIsProfiling(false);
    }
  };

  const handleExport = () => {
    if (!result) return;
    const payload = {
      generator: 'GreenCode Auditor Runtime Profiler',
      version: '2.0.0',
      standard: 'GSF SCI v1.0',
      exported_at: new Date().toISOString(),
      environment: { benchmark: selected, timeout_seconds: timeoutSec, grid_zone: zone, grid_intensity_gco2_per_kwh: result.grid_intensity_gco2_per_kwh || gridIntensity },
      metrics: {
        duration_seconds: result.duration_sec,
        avg_cpu_percent: result.avg_cpu_percent,
        peak_memory_mb: result.peak_memory_mb,
        total_power_watts: result.total_power_watts,
        energy_joules: result.energy_joules,
        energy_wh: result.energy_wh,
        operational_carbon_gco2: result.operational_carbon_gco2,
        embodied_carbon_gco2: result.embodied_carbon_gco2,
        sci_score_gco2: result.sci_score_gco2,
        exit_code: result.exit_code,
      },
      output: { stdout: result.stdout_preview || '', stderr: result.stderr_preview || '' },
    };
    const fileName = `greencode-profile-${selected}-${new Date().toISOString().replace(/[:.]/g, '-')}.json`;
    const url = URL.createObjectURL(new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setExported(`Saved ${fileName}`);
    setTimeout(() => setExported(null), 4000);
  };

  const activeBenchmark = benchmarks.find((b) => b.id === selected);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-olive">Energy Profiler</span>
            <span className="text-[11px] font-mono font-medium text-slate-500">Hardware Sandbox</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Runtime Energy Profiler</h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Run real code in an isolated sandbox to measure CPU cycles, memory footprint, and energy consumption in Joules.
          </p>
        </div>
        <div className="flex items-center gap-2.5 px-3.5 py-2 rounded-xl bg-olive-50 border border-olive-200 text-xs font-semibold text-olive-900 shadow-sm">
          <span className="w-2.5 h-2.5 rounded-full bg-olive-600 animate-pulse" />
          <span>Active Grid: <strong className="font-mono">{zone}</strong> &middot; <strong className="font-mono">{gridIntensity}</strong> gCO₂e/kWh</span>
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-900 text-sm">
          <AlertCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <p className="leading-relaxed font-medium">{error}</p>
        </div>
      )}

      {exported && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-olive-50 border border-olive-300 text-olive-900 text-xs font-semibold shadow-sm">
          <CheckCircle2 size={15} className="text-olive-700" /> {exported}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration */}
        <div className="card p-5 space-y-5">
          <div>
            <div className="flex items-center justify-between mb-1">
              <h2 className="text-sm font-bold text-slate-900">Select Benchmark Workload</h2>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-semibold">Safe Sandbox</span>
            </div>
            <p className="text-xs text-slate-500 mb-3.5">
              Choose an algorithm below to measure its live energy consumption:
            </p>
            {benchmarksLoading ? (
              <div className="flex items-center gap-2 text-sm text-slate-400 py-6 justify-center">
                <Loader2 size={18} className="animate-spin text-olive-700" /> Loading benchmarks...
              </div>
            ) : benchmarks.length === 0 ? (
              <p className="text-sm text-slate-500 py-4">No benchmark modules found.</p>
            ) : (
              <div className="space-y-2">
                {benchmarks.map((b) => {
                  const isSelected = selected === b.id;
                  return (
                    <button
                      key={b.id}
                      onClick={() => setSelected(b.id)}
                      className={`w-full text-left p-3.5 rounded-xl border transition-all text-xs ${
                        isSelected
                          ? 'border-olive-500 bg-olive-50/80 ring-1 ring-olive-500/20 text-olive-950 shadow-sm'
                          : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50/70 text-slate-800'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <p className={`font-bold ${isSelected ? 'text-olive-900' : 'text-slate-900'}`}>{b.label}</p>
                        <span className="font-mono text-[10px] text-slate-500">{b.id}</span>
                      </div>
                      <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">{b.description}</p>
                    </button>
                  );
                })}
              </div>
            )}
          </div>

          <div className="pt-2 border-t border-slate-100">
            <div className="flex justify-between items-center mb-1.5">
              <label htmlFor="timeout" className="text-xs font-bold text-slate-700 uppercase tracking-wider">
                Execution Timeout
              </label>
              <span className="font-mono text-xs font-bold text-olive-900 bg-olive-100/60 px-2 py-0.5 rounded">
                {timeoutSec}s limit
              </span>
            </div>
            <input
              id="timeout"
              type="range"
              min={5}
              max={60}
              step={5}
              value={timeoutSec}
              onChange={(e) => setTimeoutSec(Number(e.target.value))}
              className="w-full accent-olive-700 cursor-pointer"
            />
          </div>

          <button
            onClick={handleProfile}
            disabled={isProfiling || !selected}
            className="btn-primary w-full flex items-center justify-center gap-2 py-3 shadow-md disabled:opacity-50"
          >
            {isProfiling ? (
              <>
                <Loader2 size={16} className="animate-spin text-white" /> Measuring Energy...
              </>
            ) : (
              <>
                <Play size={16} className="text-white fill-white" /> Run Benchmark Test
              </>
            )}
          </button>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {!result ? (
            <div className="card p-12 flex flex-col items-center justify-center text-center">
              <div className="w-16 h-16 rounded-2xl bg-olive-50 border border-olive-200 flex items-center justify-center text-olive-700 mb-4 shadow-sm">
                <Cpu size={32} />
              </div>
              <p className="text-base font-bold text-slate-900">Ready to Benchmark</p>
              <p className="text-xs text-slate-500 mt-1.5 max-w-md leading-relaxed">
                {activeBenchmark
                  ? `Selected: "${activeBenchmark.label}". Click "Run Benchmark Test" to measure real execution time, CPU load, and energy consumption.`
                  : 'Select an algorithm on the left to start energy measurements.'}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard title="Execution Time" value={`${result.duration_sec.toFixed(2)}s`} subtitle="Total run duration" icon={<Clock size={18} />} accentColor="#1e293b" />
                <MetricCard title="CPU Load" value={`${result.avg_cpu_percent.toFixed(1)}%`} subtitle="Average processor usage" icon={<Cpu size={18} />} accentColor="#384C3B" />
                <MetricCard title="Peak Memory (RAM)" value={`${result.peak_memory_mb.toFixed(1)} MB`} subtitle="Max memory footprint" icon={<MemoryStick size={18} />} accentColor="#384C3B" />
                <MetricCard title="Energy Consumed" value={`${(result.energy_wh * 1000).toFixed(3)} mWh`} subtitle={`${result.energy_joules.toFixed(2)} Joules`} icon={<Zap size={18} />} accentColor="#384C3B" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="card p-5 flex flex-col items-center justify-center text-center">
                  <ScoreBadge score={Math.max(0, Math.min(100, result.sci_score_gco2 > 0 ? (result.sci_score_gco2 * 200) / (result.sci_score_gco2 + 100) : 100))} size="lg" />
                  <p className="label mt-3 font-bold text-slate-900">Green Score</p>
                  <p className="text-[11px] text-slate-500 mt-0.5">Software Carbon Intensity Rating</p>
                </div>
                <div className="lg:col-span-2 card p-5">
                  <div className="flex items-center justify-between mb-3">
                    <p className="label font-bold text-slate-900">Carbon &amp; Energy Breakdown</p>
                    <span className="text-[10px] font-mono font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-600">GSF SCI Standard</span>
                  </div>
                  <dl className="space-y-2.5 text-xs">
                    <div className="flex justify-between py-1 border-b border-slate-100"><dt className="text-slate-600">Operational Carbon (electricity used)</dt><dd className="font-mono font-bold text-slate-900">{result.operational_carbon_gco2.toFixed(6)} gCO₂e</dd></div>
                    <div className="flex justify-between py-1 border-b border-slate-100"><dt className="text-slate-600">Embodied Carbon (hardware lifecycle)</dt><dd className="font-mono font-bold text-slate-900">{result.embodied_carbon_gco2.toFixed(6)} gCO₂e</dd></div>
                    <div className="flex justify-between py-1 border-b border-slate-100"><dt className="font-bold text-olive-900">Total Carbon Impact</dt><dd className="font-mono font-black text-olive-800">{result.sci_score_gco2.toFixed(6)} gCO₂e</dd></div>
                    <div className="flex justify-between py-1 border-b border-slate-100"><dt className="text-slate-600">Grid Carbon Intensity</dt><dd className="font-mono text-slate-700">{result.grid_intensity_gco2_per_kwh} gCO₂e/kWh</dd></div>
                    <div className="flex justify-between py-1"><dt className="text-slate-600">Exit Status</dt><dd className="font-mono font-bold text-slate-800">{result.exit_code === 0 ? 'Success (0)' : `Code ${result.exit_code}`}</dd></div>
                  </dl>
                  <div className="flex gap-2 mt-4 pt-3 border-t border-slate-100">
                    <button onClick={handleExport} className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5 shadow-sm">
                      <Download size={13} className="text-olive-800" /> Export Benchmark Report (JSON)
                    </button>
                  </div>
                </div>
              </div>

              <div className="card overflow-hidden max-w-full">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-200/80 bg-slate-50/80">
                  <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-slate-700" />
                    <span className="text-xs font-bold text-slate-900">Sandbox Output Log</span>
                  </div>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(result.stdout_preview || '');
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                  >
                    {copied ? <CheckCircle2 size={12} className="text-olive-700" /> : <Copy size={12} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre ref={outputRef} className="p-4 text-xs font-mono text-slate-800 bg-slate-900/5 text-slate-900 overflow-x-auto max-h-64 leading-relaxed whitespace-pre-wrap break-all max-w-full">
                  {result.stdout_preview || result.stderr_preview || '(Execution completed with empty standard stream)'}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
