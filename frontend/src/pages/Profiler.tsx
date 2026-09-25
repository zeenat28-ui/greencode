import { useState, useEffect } from 'react';
import { profilerService, gridService } from '../services/greencodeApi';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { ScanResult } from '../types';
import MetricCard from '../components/common/MetricCard';
import ScoreBadge from '../components/common/ScoreBadge';
import {
  Play,
  Cpu,
  MemoryStick,
  Zap,
  Leaf,
  Download,
  Square,
  Terminal,
  Clock,
  Sparkles,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { theme } from '../styles/theme';

const PRESET_SCRIPTS = [
  { label: 'Heavy Pipeline (Baseline Anti-Patterns)', path: 'samples/heavy_pipeline.py' },
  { label: 'Eco Pipeline (Optimized Implementation)', path: 'samples/eco_pipeline.py' },
  { label: 'Heavy Pipeline Refactored (Synthesized Patch)', path: 'samples/heavy_pipeline_refactored.py' },
];

export default function Profiler() {
  const [scanData]                      = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [zone]                          = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridIntensity, setGridIntensity] = useState(215);
  const [profilingFile, setProfilingFile] = useState('samples/heavy_pipeline.py');
  const [timeoutSec, setTimeoutSec]       = useState(20);
  const [isProfiling, setIsProfiling]     = useState(false);
  const [progress, setProgress]           = useState(0);
  const [profileResult, setProfileResult] = useState<any>(null);
  const [errorMessage, setErrorMessage]   = useState<string | null>(null);
  const [copiedStdout, setCopiedStdout]   = useState(false);
  const [exportedStatus, setExportedStatus] = useState<string | null>(null);

  useEffect(() => {
    gridService
      .getZoneIntensity(zone)
      .then(r => setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? 215))
      .catch(() => setGridIntensity(215));

    const pyFiles = (scanData?.file_results || []).filter(
      (f: any) => f.language === 'python' && f.file_path
    );
    if (pyFiles.length > 0) {
      setProfilingFile(pyFiles[0].file_path);
    }
  }, [scanData, zone]);

  const handleProfile = async () => {
    if (!profilingFile) return;
    setIsProfiling(true);
    setErrorMessage(null);
    setProgress(5);

    const interval = setInterval(() => {
      setProgress(p => (p < 90 ? p + 12 : p));
    }, 400);

    try {
      const resp = await profilerService.profile(
        profilingFile,
        timeoutSec,
        zone,
        scanData?.repo_id
      );
      setProfileResult(resp.data);
      setProgress(100);
    } catch (err: any) {
      setErrorMessage(
        err.response?.data?.detail ||
          err.message ||
          'Profiling failed. Check if Python runtime is available in PATH.'
      );
      setProgress(0);
    } finally {
      clearInterval(interval);
      setIsProfiling(false);
      setTimeout(() => setProgress(0), 1500);
    }
  };

  // Bug Fix #10: Real file export producing structured JSON artifact
  const handleExportReport = () => {
    if (!profileResult) return;
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const baseName =
      (profilingFile || 'profile').split(/[\/\\]/).pop()?.replace(/\.[^/.]+$/, '') || 'script';

    const exportPayload = {
      generator: 'GreenCode Auditor Runtime Profiler',
      version: '2.0.0',
      iso_standard: 'ISO/IEC 21031:2024 / GSF SCI v1.0',
      export_timestamp: new Date().toISOString(),
      environment: {
        target_file: profilingFile,
        timeout_seconds: timeoutSec,
        grid_zone: zone,
        grid_intensity_gco2_per_kwh:
          profileResult.grid_intensity_gco2_per_kwh || gridIntensity,
      },
      metrics: {
        duration_seconds: profileResult.duration_sec,
        avg_cpu_percent: profileResult.avg_cpu_percent,
        peak_memory_mb: profileResult.peak_memory_mb,
        total_power_watts: profileResult.total_power_watts,
        energy_joules: profileResult.energy_joules,
        energy_wh: profileResult.energy_wh,
        operational_carbon_gco2: profileResult.operational_carbon_gco2,
        embodied_carbon_gco2: profileResult.embodied_carbon_gco2,
        sci_score_gco2: profileResult.sci_score_gco2,
        green_score: profileResult.green_score || 75,
        sci_grade: grade(profileResult.green_score || 75),
        exit_code: profileResult.exit_code,
      },
      output: {
        stdout: profileResult.stdout_preview || '',
        stderr: profileResult.stderr_preview || '',
      },
    };

    const fileName = `greencode-profile-${baseName}-${timestamp}.json`;
    const jsonStr = JSON.stringify(exportPayload, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = fileName;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    setExportedStatus(`Saved ${fileName}`);
    setTimeout(() => setExportedStatus(null), 4000);
  };

  const handleCopyStdout = () => {
    if (!profileResult?.stdout_preview) return;
    navigator.clipboard.writeText(profileResult.stdout_preview);
    setCopiedStdout(true);
    setTimeout(() => setCopiedStdout(false), 2000);
  };

  const grade = (s: number) =>
    s >= 90 ? 'A+' : s >= 80 ? 'A' : s >= 70 ? 'B' : s >= 60 ? 'C' : 'F';

  const pyFiles = (scanData?.file_results || []).filter(
    (f: any) => f.language === 'python' && f.file_path
  );

  return (
    <div className="space-y-6">
      {/* Page Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Runtime Profiler</h1>
          <p className="text-sm text-slate-500 mt-1">
            Execute code in a sandboxed runtime to quantify actual CPU cycles, memory, and SCI carbon impact
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="px-3 py-1.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs font-semibold text-emerald-800 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            Grid: {zone} · {gridIntensity} g/kWh
          </div>
        </div>
      </div>

      {/* Error Banner */}
      {errorMessage && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 flex items-start gap-3 text-red-800 text-sm">
          <AlertCircle size={18} className="text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="font-bold">Execution Error</p>
            <p className="text-xs text-red-600 mt-0.5 font-mono">{errorMessage}</p>
          </div>
          <button
            onClick={() => setErrorMessage(null)}
            className="text-xs text-red-600 hover:text-red-800 underline font-medium"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Profiling Configuration Card */}
      <div className="card p-6">
        <div className="flex items-center justify-between mb-5 pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-50 flex items-center justify-center text-emerald-600">
              <Cpu size={17} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-800">Profiling Target &amp; Parameters</h2>
              <p className="text-xs text-slate-400">Configure file execution harness</p>
            </div>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-slate-100 px-2 py-0.5 rounded">
            ISO/IEC 21031 Mode
          </span>
        </div>

        <div className="grid md:grid-cols-3 gap-5">
          <div className="md:col-span-2">
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Script Path or Audited File
            </label>
            {pyFiles.length > 0 ? (
              <select
                className="input text-xs font-mono"
                value={profilingFile}
                onChange={e => setProfilingFile(e.target.value)}
                disabled={isProfiling}
              >
                <optgroup label="Audited Repository Files">
                  {pyFiles.map((f: any) => (
                    <option key={f.file_path} value={f.file_path}>
                      {f.relative_path || f.file_path}
                    </option>
                  ))}
                </optgroup>
                <optgroup label="Sample Benchmarks">
                  {PRESET_SCRIPTS.map(p => (
                    <option key={p.path} value={p.path}>
                      {p.label} ({p.path})
                    </option>
                  ))}
                </optgroup>
              </select>
            ) : (
              <div className="space-y-2">
                <input
                  type="text"
                  placeholder="samples/heavy_pipeline.py"
                  className="input text-xs font-mono"
                  value={profilingFile}
                  onChange={e => setProfilingFile(e.target.value)}
                  disabled={isProfiling}
                />
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[11px] text-slate-400">Quick presets:</span>
                  {PRESET_SCRIPTS.map(p => (
                    <button
                      key={p.path}
                      type="button"
                      onClick={() => setProfilingFile(p.path)}
                      className="text-[11px] font-medium text-emerald-700 hover:text-emerald-800 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200/80 px-2 py-0.5 rounded transition-colors"
                    >
                      {p.label.split(' ')[0]}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-600 mb-1.5">
              Timeout Limit (seconds)
            </label>
            <input
              type="number"
              min={5}
              max={60}
              value={timeoutSec}
              onChange={e => setTimeoutSec(Number(e.target.value))}
              disabled={isProfiling}
              className="input text-xs font-mono"
            />
            <p className="text-[11px] text-slate-400 mt-1">Prevents runaway infinite loops</p>
          </div>
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mt-6 pt-5 border-t border-slate-100">
          <div className="flex items-center gap-4 text-xs text-slate-500">
            <span className="flex items-center gap-1.5">
              <Clock size={13} className="text-slate-400" /> Max duration: <strong>{timeoutSec}s</strong>
            </span>
            <span className="text-slate-300">·</span>
            <span className="flex items-center gap-1.5">
              <Leaf size={13} className="text-emerald-600" /> Carbon factor: <strong>{gridIntensity} g/kWh</strong>
            </span>
          </div>

          <button
            onClick={handleProfile}
            disabled={isProfiling || !profilingFile}
            className="btn-primary flex items-center justify-center gap-2 text-xs font-semibold px-5 py-2.5 disabled:opacity-50"
          >
            {isProfiling ? (
              <>
                <Square size={14} className="text-white animate-pulse" />
                Executing Sandbox...
              </>
            ) : (
              <>
                <Play size={14} className="fill-white" />
                Run Benchmark Profile
              </>
            )}
          </button>
        </div>

        {isProfiling && (
          <div className="mt-4 pt-3 border-t border-slate-100">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1.5">
              <span>Sampling CPU &amp; RAM telemetry...</span>
              <span className="font-mono">{progress}%</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-300 bg-emerald-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Profiling Results */}
      {profileResult && (
        <div className="space-y-5">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <h2 className="text-lg font-extrabold text-slate-900">Execution Telemetry</h2>
              <span
                className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                  profileResult.exit_code === 0
                    ? 'bg-emerald-100 text-emerald-800'
                    : 'bg-red-100 text-red-800'
                }`}
              >
                Exit Code: {profileResult.exit_code}
              </span>
            </div>

            {/* Export and Status Feedback */}
            <div className="flex items-center gap-2">
              {exportedStatus && (
                <span className="text-xs font-semibold text-emerald-600 flex items-center gap-1">
                  <CheckCircle2 size={13} /> {exportedStatus}
                </span>
              )}
              <button
                onClick={handleExportReport}
                className="btn-secondary flex items-center gap-2 text-xs font-semibold px-3 py-2"
                title="Download JSON report for CI/CD audit logs"
              >
                <Download size={14} /> Export Report (.json)
              </button>
            </div>
          </div>

          {/* Metric Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="Execution Time"
              value={`${profileResult.duration_sec.toFixed(3)} s`}
              subtitle="Wall clock runtime"
              icon={<Play size={18} />}
            />
            <MetricCard
              title="Avg CPU Utilization"
              value={`${profileResult.avg_cpu_percent.toFixed(1)}%`}
              subtitle="Multi-core normalized"
              icon={<Cpu size={18} />}
              accentColor={profileResult.avg_cpu_percent > 70 ? '#d97706' : undefined}
            />
            <MetricCard
              title="Peak Memory"
              value={`${profileResult.peak_memory_mb.toFixed(1)} MB`}
              subtitle="Resident set size (RSS)"
              icon={<MemoryStick size={18} />}
            />
            <MetricCard
              title="Total Power Draw"
              value={`${profileResult.total_power_watts.toFixed(2)} W`}
              subtitle="Calculated hardware load"
              icon={<Zap size={18} />}
            />
            <MetricCard
              title="Energy Consumed"
              value={`${(profileResult.energy_wh * 1000).toFixed(2)} mWh`}
              subtitle={`${(profileResult.energy_joules || profileResult.energy_wh * 3600).toFixed(1)} Joules`}
              icon={<Zap size={18} />}
              accentColor="#d97706"
            />
            <MetricCard
              title="Operational Carbon"
              value={`${profileResult.operational_carbon_gco2.toFixed(4)} g`}
              subtitle="Grid emission per run"
              icon={<Leaf size={18} />}
              accentColor="#059669"
            />
            <MetricCard
              title="Embodied Carbon"
              value={`${profileResult.embodied_carbon_gco2.toFixed(4)} g`}
              subtitle="Device manufacturing share"
              icon={<Leaf size={18} />}
              accentColor="#059669"
            />
            <MetricCard
              title="SCI Rating (GSF)"
              value={`${(profileResult.sci_score_gco2 * 1000).toFixed(2)} mg`}
              subtitle={`Grade: ${grade(profileResult.green_score || 75)}`}
              icon={<Sparkles size={18} />}
              accentColor="#0284c7"
            />
          </div>

          {/* Stdout / Stderr Previews */}
          <div className="grid md:grid-cols-2 gap-4">
            {profileResult.stdout_preview ? (
              <div className="card p-5">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-700 uppercase tracking-wider">
                    <Terminal size={13} className="text-slate-500" />
                    Standard Output
                  </div>
                  <button
                    onClick={handleCopyStdout}
                    className="text-[11px] text-slate-500 hover:text-slate-800 transition-colors"
                  >
                    {copiedStdout ? 'Copied!' : 'Copy'}
                  </button>
                </div>
                <pre className="text-xs font-mono text-slate-700 bg-slate-900 text-slate-100 p-3.5 rounded-lg overflow-x-auto leading-relaxed max-h-56">
                  {profileResult.stdout_preview}
                </pre>
              </div>
            ) : null}

            {profileResult.stderr_preview ? (
              <div className="card p-5 border-red-200">
                <div className="flex items-center gap-1.5 text-xs font-semibold text-red-600 uppercase tracking-wider mb-2">
                  <AlertCircle size={13} />
                  Standard Error
                </div>
                <pre className="text-xs font-mono text-red-700 bg-red-50 p-3.5 rounded-lg border border-red-200 overflow-x-auto leading-relaxed max-h-56">
                  {profileResult.stderr_preview}
                </pre>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
