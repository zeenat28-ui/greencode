import { useState, useEffect } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { gridService, githubService } from '../services/greencodeApi';
import { ZoneData } from '../types';
import { save } from '../utils/storage';
import {
  Key, Save, Globe, CheckCircle, Eye, EyeOff,
  AlertCircle, Loader2, ShieldCheck, Github, Zap, RefreshCw, Sparkles
} from 'lucide-react';
import { GRID_ZONES } from '../styles/theme';

export default function Settings() {
  const [emApiKey, setEmApiKey]           = useLocalStorage('greencode_em_key', '');
  const [hfApiKey, setHfApiKey]           = useLocalStorage('greencode_hf_key', '');
  const [ghToken, setGhToken]             = useLocalStorage('greencode_gh_token', '');
  const [qualityThreshold, setQualityThreshold] = useLocalStorage('greencode_threshold', 75);
  const [selectedZone, setSelectedZone]   = useLocalStorage('greencode_zone', 'US-CAL-CISO');

  const [gridData, setGridData]           = useState<ZoneData | null>(null);
  const [gridLoading, setGridLoading]     = useState(false);
  const [showEmKey, setShowEmKey]         = useState(false);
  const [showHfKey, setShowHfKey]         = useState(false);
  const [showGhToken, setShowGhToken]     = useState(false);
  const [saved, setSaved]                 = useState(false);

  // Bug fix #6: Electricity Maps key test with real status & message
  const [emTestStatus, setEmTestStatus]   = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [emTestFeedback, setEmTestFeedback] = useState<string | null>(null);

  // GitHub token test status
  const [ghTestStatus, setGhTestStatus]   = useState<'idle' | 'testing' | 'success' | 'error'>('idle');
  const [ghTestFeedback, setGhTestFeedback] = useState<string | null>(null);

  useEffect(() => {
    loadGridData();
  }, [selectedZone]);

  const loadGridData = async () => {
    setGridLoading(true);
    try {
      const resp = await gridService.getZoneIntensity(selectedZone, emApiKey || undefined);
      setGridData(resp.data);
    } catch {
      setGridData(null);
    } finally {
      setGridLoading(false);
    }
  };

  // Bug fix #6: Explicit test using the key currently entered in the input field
  const handleTestEmKey = async () => {
    const keyToTest = emApiKey.trim();
    if (!keyToTest) {
      setEmTestStatus('error');
      setEmTestFeedback('Please enter an Electricity Maps API key to test.');
      return;
    }

    setEmTestStatus('testing');
    setEmTestFeedback(null);

    try {
      const resp = await gridService.getZoneIntensity(selectedZone, keyToTest);
      const d = resp.data;
      setGridData(d);
      setEmTestStatus('success');
      setEmTestFeedback(
        `Verified! Connected to ${d.name} (${d.marginal_carbon_intensity ?? d.carbon_intensity} gCO₂/kWh · ${d.is_live ? 'Live Stream Active' : 'Baseline Verified'})`
      );
    } catch (err: any) {
      setEmTestStatus('error');
      setEmTestFeedback(
        err.response?.data?.detail || 'Connection failed. Please verify your Electricity Maps API key and zone.'
      );
    }
  };

  const handleTestGhToken = async () => {
    const tokenToTest = (ghToken as string || '').trim();
    if (!tokenToTest) {
      setGhTestStatus('error');
      setGhTestFeedback('Please enter a GitHub Personal Access Token to test.');
      return;
    }

    setGhTestStatus('testing');
    setGhTestFeedback(null);

    try {
      const resp = await githubService.getAuthenticatedUser(tokenToTest);
      const user = resp.data.user;
      setGhTestStatus('success');
      setGhTestFeedback(`Verified as @${user?.login} (${user?.name || 'GitHub User'}) · ${user?.public_repos} Public Repos`);
    } catch (err: any) {
      setGhTestStatus('error');
      setGhTestFeedback(err.response?.data?.detail || 'GitHub token verification failed. Ensure the token has repo scope.');
    }
  };

  const handleSave = () => {
    save('greencode_settings', {
      emApiKey,
      hfApiKey,
      ghToken: ghToken as string,
      qualityThreshold,
      selectedZone
    });
    setSaved(true);
    setTimeout(() => setSaved(false), 3000);
  };

  const getThresholdColor = (val: number) => {
    if (val >= 90) return 'text-emerald-600 bg-emerald-50 border-emerald-200';
    if (val >= 80) return 'text-emerald-700 bg-emerald-50 border-emerald-200';
    if (val >= 70) return 'text-amber-700 bg-amber-50 border-amber-200';
    return 'text-red-700 bg-red-50 border-red-200';
  };

  const getThresholdGrade = (val: number) => {
    if (val >= 90) return 'A+';
    if (val >= 80) return 'A';
    if (val >= 70) return 'B';
    if (val >= 60) return 'C';
    return 'F';
  };

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Platform Settings</h1>
          <p className="text-sm text-slate-500 mt-1">
            Configure live electricity telemetry, automated Pull Request credentials, and CI/CD quality gate rules.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {saved && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl animate-in fade-in">
              <CheckCircle size={14} className="text-emerald-600" /> Settings Saved!
            </span>
          )}
          <button
            onClick={handleSave}
            className="btn-primary flex items-center gap-2 text-xs py-2.5 px-5 shadow-sm"
          >
            <Save size={14} /> Save Configuration
          </button>
        </div>
      </div>

      {/* 2-Column Responsive Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">

        {/* Left Column: API Credentials & Integrations (7 cols) */}
        <div className="lg:col-span-7 space-y-5">

          {/* Electricity Maps Card */}
          <div className="card p-6 shadow-sm border-slate-200/80 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                  <Globe size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Electricity Maps API</h2>
                  <p className="text-[11px] text-slate-400">Live regional carbon intensity telemetry</p>
                </div>
              </div>
              <a
                href="https://www.electricitymaps.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-900 hover:underline"
              >
                electricitymaps.com &rarr;
              </a>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Electricity Maps API Key
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showEmKey ? 'text' : 'password'}
                    placeholder="Enter your Electricity Maps API key"
                    className="input pr-10 text-xs font-mono"
                    value={emApiKey}
                    onChange={e => {
                      setEmApiKey(e.target.value);
                      setEmTestStatus('idle');
                      setEmTestFeedback(null);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowEmKey(!showEmKey)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showEmKey ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleTestEmKey}
                  disabled={emTestStatus === 'testing'}
                  className="btn-secondary text-xs px-4 py-2 shrink-0"
                >
                  {emTestStatus === 'testing' ? (
                    <>
                      <Loader2 size={13} className="animate-spin text-emerald-600" /> Testing...
                    </>
                  ) : (
                    'Test Connection'
                  )}
                </button>
              </div>

              {emTestFeedback && (
                <div className={`mt-2.5 p-3 rounded-xl text-xs flex items-start gap-2.5 ${
                  emTestStatus === 'success'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {emTestStatus === 'success' ? (
                    <CheckCircle size={15} className="text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                  )}
                  <span className="leading-relaxed font-medium">{emTestFeedback}</span>
                </div>
              )}

              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                When provided, GreenCode streams real-time marginal carbon intensity (gCO₂/kWh) from regional electricity grids. If omitted, verified baseline coefficients are used.
              </p>
            </div>
          </div>

          {/* GitHub Integration Card */}
          <div className="card p-6 shadow-sm border-slate-200/80 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-slate-100 text-slate-800 flex items-center justify-center font-bold">
                  <Github size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">GitHub Access Token</h2>
                  <p className="text-[11px] text-slate-400">Automated Pull Request creation &amp; private repo audits</p>
                </div>
              </div>
              <a
                href="https://github.com/settings/tokens"
                target="_blank"
                rel="noopener noreferrer"
                className="text-[11px] font-semibold text-emerald-700 hover:text-emerald-900 hover:underline"
              >
                Create PAT &rarr;
              </a>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Personal Access Token (Classic or Fine-Grained)
              </label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <input
                    type={showGhToken ? 'text' : 'password'}
                    placeholder="ghp_..."
                    className="input pr-10 text-xs font-mono"
                    value={ghToken}
                    onChange={e => {
                      setGhToken(e.target.value);
                      setGhTestStatus('idle');
                      setGhTestFeedback(null);
                    }}
                  />
                  <button
                    type="button"
                    onClick={() => setShowGhToken(!showGhToken)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showGhToken ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
                <button
                  type="button"
                  onClick={handleTestGhToken}
                  disabled={ghTestStatus === 'testing'}
                  className="btn-secondary text-xs px-4 py-2 shrink-0"
                >
                  {ghTestStatus === 'testing' ? (
                    <>
                      <Loader2 size={13} className="animate-spin text-slate-600" /> Verifying...
                    </>
                  ) : (
                    'Verify Token'
                  )}
                </button>
              </div>

              {ghTestFeedback && (
                <div className={`mt-2.5 p-3 rounded-xl text-xs flex items-start gap-2.5 ${
                  ghTestStatus === 'success'
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {ghTestStatus === 'success' ? (
                    <CheckCircle size={15} className="text-emerald-600 shrink-0 mt-0.5" />
                  ) : (
                    <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                  )}
                  <span className="leading-relaxed font-medium">{ghTestFeedback}</span>
                </div>
              )}

              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                Requires <code className="bg-slate-100 px-1 py-0.5 rounded text-[11px] font-mono">repo</code> permissions to commit eco-refactored patches and open automated Pull Requests.
              </p>
            </div>
          </div>

          {/* IBM Bob & Hugging Face Card */}
          <div className="card p-6 shadow-sm border-slate-200/80 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-xl bg-blue-50 text-blue-700 flex items-center justify-center font-bold">
                <Zap size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">AI Code Synthesis Engines</h2>
                <p className="text-[11px] text-slate-400">IBM Granite 3.2 Code &middot; Qwen 2.5 Coder &middot; AST Transformer</p>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Model API Token (Optional)
              </label>
              <div className="relative">
                <input
                  type={showHfKey ? 'text' : 'password'}
                  placeholder="hf_... (optional custom inference token)"
                  className="input pr-10 text-xs font-mono"
                  value={hfApiKey}
                  onChange={e => setHfApiKey(e.target.value)}
                />
                <button
                  type="button"
                  onClick={() => setShowHfKey(!showHfKey)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showHfKey ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="text-[11px] text-slate-400 mt-2 leading-relaxed">
                By default, GreenCode utilizes the built-in IBM Bob 2.0 Plan Mode engine and AST synthesizer with zero external token requirement.
              </p>
            </div>
          </div>

        </div>

        {/* Right Column: Grid Telemetry & Quality Gate (5 cols) */}
        <div className="lg:col-span-5 space-y-5">

          {/* Regional Grid Telemetry */}
          <div className="card p-6 shadow-sm border-slate-200/80 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                  <Globe size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Regional Electricity Grid</h2>
                  <p className="text-[11px] text-slate-400">Operational emissions coefficient</p>
                </div>
              </div>
              <button
                onClick={loadGridData}
                disabled={gridLoading}
                className="text-slate-400 hover:text-slate-600 p-1"
                title="Refresh grid telemetry"
              >
                <RefreshCw size={13} className={gridLoading ? 'animate-spin' : ''} />
              </button>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Select Grid Zone
              </label>
              <select
                className="input text-xs font-medium"
                value={selectedZone}
                onChange={e => setSelectedZone(e.target.value)}
              >
                {GRID_ZONES.map(z => (
                  <option key={z.value} value={z.value}>{z.label} &mdash; ({z.value})</option>
                ))}
              </select>
            </div>

            {/* Grid Live Metrics Box */}
            {gridData && (
              <div className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/80 space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${gridData.is_live ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
                    <span className="font-bold text-xs text-slate-900 truncate max-w-[180px]">
                      {gridData.name}
                    </span>
                  </div>
                  <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    gridData.is_live ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-200 text-slate-700'
                  }`}>
                    {gridData.is_live ? 'Live Feed' : 'Baseline Verified'}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2.5 text-xs pt-1">
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200/70">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Intensity</span>
                    <span className="font-black text-slate-900 text-base">
                      {gridData.marginal_carbon_intensity ?? gridData.carbon_intensity}
                    </span>
                    <span className="text-[10px] text-slate-400 ml-1">gCO₂/kWh</span>
                  </div>
                  <div className="bg-white p-2.5 rounded-lg border border-slate-200/70">
                    <span className="text-[10px] text-slate-400 uppercase tracking-wider block font-semibold">Clean Energy</span>
                    <span className="font-black text-emerald-700 text-base">
                      {gridData.clean_energy_percentage}%
                    </span>
                    <span className="text-[10px] text-slate-400 ml-1">Renewables</span>
                  </div>
                </div>

                {gridData.time_of_day_info?.recommendation && (
                  <p className="text-[11px] text-slate-500 italic bg-white/70 p-2.5 rounded-lg border border-slate-200/60 leading-relaxed">
                    💡 {gridData.time_of_day_info.recommendation}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* CI/CD Quality Gate Threshold */}
          <div className="card p-6 shadow-sm border-slate-200/80 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">CI/CD Quality Gate</h2>
                <p className="text-[11px] text-slate-400">Green Score passing threshold for merge</p>
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-2">
                <label className="text-xs font-bold uppercase tracking-wider text-slate-700">
                  Minimum Score (0-100)
                </label>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-extrabold px-2 py-0.5 rounded-md border ${getThresholdColor(qualityThreshold)}`}>
                    Grade {getThresholdGrade(qualityThreshold)}
                  </span>
                  <span className="text-lg font-black text-slate-900">{qualityThreshold}</span>
                </div>
              </div>

              <input
                type="range"
                min={50}
                max={95}
                step={5}
                value={qualityThreshold}
                onChange={e => setQualityThreshold(Number(e.target.value))}
                className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-emerald-600"
              />

              <div className="flex justify-between text-[10px] font-semibold text-slate-400 mt-1.5 px-0.5">
                <span>50 (Permissive)</span>
                <span>75 (Recommended)</span>
                <span>95 (Strict)</span>
              </div>

              <p className="text-[11px] text-slate-400 mt-3 leading-relaxed">
                CI/CD workflows running <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-[10px]">--ci</code> exit with code 1 and block GitHub pull requests if the audited Green Score drops below <strong>{qualityThreshold}</strong>.
              </p>
            </div>
          </div>

        </div>

      </div>

    </div>
  );
}
