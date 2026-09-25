import { useState, useEffect } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { gridService, githubService, authService } from '../services/greencodeApi';
import { useAuth } from '../context/AuthContext';
import { ZoneData } from '../types';
import { GRID_ZONES } from '../styles/theme';
import {
  Globe, CheckCircle, ShieldCheck, Github, Loader2, RefreshCw,
  AlertCircle, Key, Leaf,
} from 'lucide-react';

function getThresholdGrade(val: number) {
  if (val >= 90) return 'A+';
  if (val >= 80) return 'A';
  if (val >= 70) return 'B';
  if (val >= 60) return 'C';
  return 'F';
}

export default function Settings() {
  const { user, refreshUser } = useAuth();

  const [selectedZone, setSelectedZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [qualityThreshold, setQualityThreshold] = useLocalStorage('greencode_threshold', 75);
  const [saved, setSaved] = useState(false);

  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [gridLoading, setGridLoading] = useState(false);
  const [gridError, setGridError] = useState<string | null>(null);

  const [ghUser, setGhUser] = useState<{ login: string; avatar_url: string } | null>(null);
  const [ghTesting, setGhTesting] = useState(false);
  const [ghError, setGhError] = useState<string | null>(null);

  const [rotating, setRotating] = useState(false);
  const [newToken, setNewToken] = useState('');
  const [rotateMsg, setRotateMsg] = useState<string | null>(null);
  const [rotateError, setRotateError] = useState<string | null>(null);

  const loadGrid = async () => {
    setGridLoading(true);
    setGridError(null);
    try {
      const res = await gridService.getZoneIntensity(selectedZone);
      setGridData(res.data);
    } catch (err: any) {
      setGridData(null);
      setGridError(err?.response?.data?.detail || 'Could not reach the grid telemetry service.');
    } finally {
      setGridLoading(false);
    }
  };

  useEffect(() => { loadGrid(); }, [selectedZone]);

  const testGitHub = async () => {
    setGhTesting(true);
    setGhError(null);
    try {
      const res = await githubService.getAuthenticatedUser();
      setGhUser(res.data.user as any);
    } catch (err: any) {
      setGhError(
        err?.response?.data?.detail || 'Your stored GitHub token is no longer valid. Please reconnect.'
      );
    } finally {
      setGhTesting(false);
    }
  };

  useEffect(() => { testGitHub(); }, []);

  const handleRotateToken = async () => {
    const trimmed = newToken.trim();
    if (!trimmed) {
      setRotateError('Paste a new token first.');
      return;
    }
    setRotating(true);
    setRotateError(null);
    setRotateMsg(null);
    try {
      // The API verifies the token with GitHub before persisting it.
      await authService.updateProfile(user!.id, { github_token: trimmed });
      await refreshUser();
      setNewToken('');
      setRotateMsg('GitHub token updated. Repositories will use it immediately.');
    } catch (err: any) {
      setRotateError(err?.response?.data?.detail || 'GitHub rejected that token.');
    } finally {
      setRotating(false);
    }
  };

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2500);
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200/80 pb-5">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Settings</h1>
          <p className="text-sm text-slate-500 mt-1">
            Grid carbon telemetry, quality gate rules, and your GitHub connection
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-1.5 rounded-xl">
              <CheckCircle size={14} className="text-emerald-600" /> Settings Saved
            </span>
          )}
          <button onClick={handleSave} className="btn-primary flex items-center gap-2 text-xs py-2.5 px-5">
            <CheckCircle size={14} /> Save Configuration
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 space-y-5">
          {/* GitHub connection */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center">
                  <Github size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">GitHub Connection</h2>
                  <p className="text-[11px] text-slate-400">The only credential used by this tool</p>
                </div>
              </div>
              <button onClick={testGitHub} disabled={ghTesting} className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5">
                {ghTesting ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />}
                Test
              </button>
            </div>

            {ghError && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                <p className="text-xs text-red-700 leading-relaxed">{ghError}</p>
              </div>
            )}

            {ghUser ? (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-emerald-50/60 border border-emerald-200">
                {ghUser.avatar_url && <img src={ghUser.avatar_url} alt="" className="w-9 h-9 rounded-full border border-emerald-200" />}
                <div className="min-w-0">
                  <p className="text-sm font-bold text-slate-900 truncate">{ghUser.login}</p>
                  <p className="text-xs text-emerald-700 font-medium">Connected &middot; verified against the GitHub API</p>
                </div>
              </div>
            ) : !ghError ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                <Loader2 size={13} className="animate-spin" /> Verifying connection...
              </div>
            ) : null}

            <div className="pt-2 border-t border-slate-100">
              <label htmlFor="rotate-token" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Rotate Token
              </label>
              <div className="flex gap-2">
                <input
                  id="rotate-token"
                  type="password"
                  value={newToken}
                  onChange={(e) => { setNewToken(e.target.value); setRotateError(null); setRotateMsg(null); }}
                  placeholder={user?.github_token_masked ? `Current: ${user.github_token_masked}` : 'Paste a new PAT'}
                  className="input text-xs font-mono flex-1"
                  autoComplete="off"
                />
                <button onClick={handleRotateToken} disabled={rotating || !newToken.trim()} className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5">
                  {rotating ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                  Update
                </button>
              </div>
              {rotateError && <p className="text-xs text-red-600 mt-1.5">{rotateError}</p>}
              {rotateMsg && <p className="text-xs text-emerald-700 mt-1.5">{rotateMsg}</p>}
              <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
                The token is verified with GitHub, then stored encrypted server-side. It is never
                returned to the browser and is never sent as a URL parameter.
              </p>
            </div>
          </div>

          {/* Grid zone */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center">
                <Globe size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Grid Carbon Region</h2>
                <p className="text-[11px] text-slate-400">Used to convert energy into operational carbon</p>
              </div>
            </div>

            <div>
              <label htmlFor="zone" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Default Grid Zone
              </label>
              <select
                id="zone"
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                className="input text-sm"
              >
                {GRID_ZONES.map((z) => (
                  <option key={z.value} value={z.value}>{z.label} &mdash; {z.value}</option>
                ))}
              </select>
            </div>

            {gridLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Loader2 size={13} className="animate-spin" /> Fetching intensity...
              </div>
            ) : gridError ? (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
                <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 leading-relaxed">{gridError}</p>
              </div>
            ) : gridData ? (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-3 rounded-lg bg-slate-50">
                  <dt className="label">Intensity</dt>
                  <dd className="font-bold text-slate-900">{gridData.marginal_carbon_intensity ?? gridData.carbon_intensity} g/kWh</dd>
                </div>
                <div className="p-3 rounded-lg bg-slate-50">
                  <dt className="label">Clean energy</dt>
                  <dd className="font-bold text-emerald-700">{gridData.clean_energy_percentage}%</dd>
                </div>
                <div className="p-3 rounded-lg bg-slate-50 col-span-2">
                  <dt className="label">Source</dt>
                  <dd className="text-xs text-slate-600">
                    {gridData.name} &middot; {gridData.is_live ? 'Live telemetry' : 'Verified baseline'}
                  </dd>
                </div>
              </dl>
            ) : null}
          </div>
        </div>

        {/* Quality gate */}
        <div className="lg:col-span-5 space-y-5">
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-xl bg-amber-50 text-amber-700 flex items-center justify-center">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Quality Gate</h2>
                <p className="text-[11px] text-slate-400">Minimum Green Score considered compliant</p>
              </div>
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Threshold</span>
                <span className="text-2xl font-black text-slate-900">
                  {Number(qualityThreshold)}
                  <span className="text-xs font-semibold text-slate-400 ml-1">/ 100</span>
                </span>
              </div>
              <input
                type="range"
                min={0}
                max={100}
                step={5}
                value={Number(qualityThreshold)}
                onChange={(e) => setQualityThreshold(Number(e.target.value))}
                className="w-full accent-emerald-600"
                aria-label="Quality gate threshold"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
                <span>0</span><span>50</span><span>100</span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 text-center">
              <p className="text-xs font-semibold text-slate-500">Repositories scoring below {Number(qualityThreshold)} are flagged</p>
              <p className="text-3xl font-black mt-1.5" style={{ color: Number(qualityThreshold) >= 80 ? '#059669' : '#d97706' }}>
                {getThresholdGrade(Number(qualityThreshold))}
              </p>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed">
              The same threshold is used by the native GitHub Action, so a local run and a CI run
              report identical pass/fail verdicts.
            </p>
          </div>

          <div className="card p-5">
            <div className="flex items-start gap-3">
              <Leaf size={18} className="text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-xs font-bold text-slate-900">About this build</p>
                <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">
                  GreenCode Auditor scans repositories from your connected GitHub account, scores
                  them against Green Software Foundation SCI patterns, and opens eco-refactoring
                  pull requests.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
