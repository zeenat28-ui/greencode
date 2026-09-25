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
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Runtime Profiler</h1>
          <p className="text-sm text-slate-500 mt-1">
            Measure real CPU, memory and carbon cost by executing reference benchmarks in a sandbox
          </p>
        </div>
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          Grid: {zone} &middot; {gridIntensity} g/kWh
        </div>
      </div>

      {error && (
        <div role="alert" className="flex items-start gap-3 p-4 rounded-xl bg-red-50 border border-red-200 text-red-800 text-sm">
          <AlertCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <p className="leading-relaxed">{error}</p>
        </div>
      )}

      {exported && (
        <div className="flex items-center gap-2 px-4 py-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-xs font-medium">
          <CheckCircle2 size={14} /> {exported}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Configuration */}
        <div className="card p-5 space-y-5">
          <div>
            <h2 className="text-sm font-bold text-slate-900">Benchmark</h2>
            <p className="text-xs text-slate-500 mt-0.5 mb-3">
              Only bundled reference scripts can be executed
            </p>
            {benchmarksLoading ? (
              <div className="flex items-center gap-2 text-sm text-slate-400 py-4">
                <Loader2 size={16} className="animate-spin" /> Loading benchmarks...
              </div>
            ) : benchmarks.length === 0 ? (
              <p className="text-sm text-slate-500 py-4">No benchmarks are available on this server.</p>
            ) : (
              <div className="space-y-2">
                {benchmarks.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => setSelected(b.id)}
                    className={`w-full text-left p-3 rounded-lg border transition-colors ${
                      selected === b.id
                        ? 'border-emerald-300 bg-emerald-50'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <p className="text-sm font-semibold text-slate-900">{b.label}</p>
                    <p className="text-xs text-slate-500 mt-0.5 leading-relaxed">{b.description}</p>
                  </button>
                ))}
              </div>
            )}
          </div>

          <div>
            <label htmlFor="timeout" className="label mb-1.5">
              Timeout: {timeoutSec}s
            </label>
            <input
              id="timeout"
              type="range"
              min={5}
              max={60}
              step={5}
              value={timeoutSec}
              onChange={(e) => setTimeoutSec(Number(e.target.value))}
              className="w-full accent-emerald-600"
            />
          </div>

          <button
            onClick={handleProfile}
            disabled={isProfiling || !selected}
            className="btn-primary w-full flex items-center justify-center gap-2"
          >
            {isProfiling ? (
              <>
                <Loader2 size={15} className="animate-spin" /> Executing...
              </>
            ) : (
              <>
                <Play size={15} /> Run Profiler
              </>
            )}
          </button>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-5">
          {!result ? (
            <div className="card p-12 flex flex-col items-center justify-center text-center">
              <Cpu size={30} className="text-slate-300 mb-3" />
              <p className="text-sm font-semibold text-slate-700">No profiling run yet</p>
              <p className="text-xs text-slate-500 mt-1 max-w-sm">
                {activeBenchmark
                  ? `Select "${activeBenchmark.label}" and run the profiler to capture SCI telemetry.`
                  : 'Choose a benchmark and run the profiler to capture SCI telemetry.'}
              </p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <MetricCard title="Duration" value={`${result.duration_sec.toFixed(2)}s`} icon={<Clock size={18} />} accentColor="#0f172a" />
                <MetricCard title="Avg CPU" value={`${result.avg_cpu_percent.toFixed(1)}%`} icon={<Cpu size={18} />} accentColor="#d97706" />
                <MetricCard title="Peak Memory" value={`${result.peak_memory_mb.toFixed(1)} MB`} icon={<MemoryStick size={18} />} accentColor="#7c3aed" />
                <MetricCard title="Energy" value={`${(result.energy_wh * 1000).toFixed(3)} mWh`} icon={<Zap size={18} />} accentColor="#059669" />
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                <div className="card p-5 flex flex-col items-center">
                  <ScoreBadge score={Math.max(0, Math.min(100, result.sci_score_gco2 > 0 ? (result.sci_score_gco2 * 200) / (result.sci_score_gco2 + 100) : 100))} size="md" />
                  <p className="label mt-3 text-center">SCI Score</p>
                </div>
                <div className="lg:col-span-2 card p-5">
                  <p className="label mb-3">Carbon Breakdown</p>
                  <dl className="space-y-2.5 text-sm">
                    <div className="flex justify-between"><dt className="text-slate-600">Operational</dt><dd className="font-mono font-semibold text-slate-900">{result.operational_carbon_gco2.toFixed(6)} gCO2e</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-600">Embodied</dt><dd className="font-mono font-semibold text-slate-900">{result.embodied_carbon_gco2.toFixed(6)} gCO2e</dd></div>
                    <div className="flex justify-between border-t border-slate-100 pt-2.5"><dt className="font-bold text-slate-800">Total SCI</dt><dd className="font-mono font-bold text-emerald-700">{result.sci_score_gco2.toFixed(6)} gCO2e</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-600">Grid intensity</dt><dd className="font-mono text-slate-700">{result.grid_intensity_gco2_per_kwh} gCO2e/kWh</dd></div>
                    <div className="flex justify-between"><dt className="text-slate-600">Exit code</dt><dd className="font-mono text-slate-700">{result.exit_code}</dd></div>
                  </dl>
                  <div className="flex gap-2 mt-4 pt-4 border-t border-slate-100">
                    <button onClick={handleExport} className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"><Download size={12} /> Export JSON</button>
                  </div>
                </div>
              </div>

              <div className="card overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100 bg-slate-50">
                  <div className="flex items-center gap-2">
                    <Terminal size={14} className="text-slate-500" />
                    <span className="text-xs font-bold text-slate-800">Program Output</span>
                  </div>
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(result.stdout_preview || '');
                      setCopied(true);
                      setTimeout(() => setCopied(false), 2000);
                    }}
                    className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                  >
                    {copied ? <CheckCircle2 size={11} /> : <Copy size={11} />}
                    {copied ? 'Copied' : 'Copy'}
                  </button>
                </div>
                <pre ref={outputRef} className="p-4 text-xs font-mono text-slate-700 bg-slate-50 overflow-x-auto max-h-64 leading-relaxed">
                  {result.stdout_preview || result.stderr_preview || '(no output)'}
                </pre>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
