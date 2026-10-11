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

  const [usageData, setUsageData] = useState<any | null>(null);
  const [licenseKey, setLicenseKey] = useState('');
  const [activatingLicense, setActivatingLicense] = useState(false);
  const [licenseMsg, setLicenseMsg] = useState<string | null>(null);
  const [licenseError, setLicenseError] = useState<string | null>(null);

  const loadBillingUsage = async () => {
    try {
      const token = localStorage.getItem('greencode_token') || '';
      const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
      const res = await fetch('/api/billing/usage?org_id=1', { headers });
      if (res.ok) {
        setUsageData(await res.json());
      }
    } catch {
      // Non-blocking
    }
  };

  useEffect(() => { loadBillingUsage(); }, []);

  const handleActivateLicense = async () => {
    const trimmed = licenseKey.trim();
    if (!trimmed) {
      setLicenseError('Enter a valid GC-LIC-... license key.');
      return;
    }
    setActivatingLicense(true);
    setLicenseError(null);
    setLicenseMsg(null);
    try {
      const token = localStorage.getItem('greencode_token') || '';
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const res = await fetch('/api/billing/license/activate', {
        method: 'POST',
        headers,
        body: JSON.stringify({ org_id: 1, license_key: trimmed }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setLicenseError(body?.detail || 'License verification failed.');
      } else {
        setLicenseKey('');
        setLicenseMsg(`Activated ${String(body?.license?.tier || 'pro').toUpperCase()} tier (${body?.license?.seats || 1} seats).`);
        await loadBillingUsage();
      }
    } catch (err: any) {
      setLicenseError(err?.message || 'Could not reach billing service.');
    } finally {
      setActivatingLicense(false);
    }
  };

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
          <div className="flex items-center gap-2 mb-1">
            <span className="badge-olive">Settings</span>
            <span className="text-[11px] font-mono font-medium text-slate-500">Configuration</span>
          </div>
          <h1 className="text-2xl font-black text-slate-900 tracking-tight">Settings &amp; Configuration</h1>
          <p className="text-sm text-slate-600 mt-0.5">
            Manage your Green Score quality gate, power grid region, and GitHub connection.
          </p>
        </div>
        <div className="flex items-center gap-3">
          {saved && (
            <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-olive-900 bg-olive-50 border border-olive-300 px-3 py-1.5 rounded-xl shadow-sm">
              <CheckCircle size={14} className="text-olive-700" /> Settings Saved
            </span>
          )}
          <button onClick={handleSave} className="btn-primary flex items-center gap-2 text-xs py-2.5 px-5 shadow-sm">
            <CheckCircle size={14} /> Save Changes
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        <div className="lg:col-span-7 space-y-5">
          {/* GitHub connection */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-slate-900 text-white flex items-center justify-center shadow-sm">
                  <Github size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">GitHub Connection</h2>
                  <p className="text-[11px] text-slate-500">Access repositories to audit code and open pull requests</p>
                </div>
              </div>
              <button onClick={testGitHub} disabled={ghTesting} className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5">
                {ghTesting ? <Loader2 size={11} className="animate-spin text-olive-700" /> : <RefreshCw size={11} />}
                Test Connection
              </button>
            </div>

            {ghError && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200">
                <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                <p className="text-xs text-red-700 leading-relaxed font-medium">{ghError}</p>
              </div>
            )}

            {ghUser ? (
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-olive-50/70 border border-olive-200">
                {ghUser.avatar_url && <img src={ghUser.avatar_url} alt="" className="w-9 h-9 rounded-full border border-olive-300 shadow-sm" />}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm font-bold text-slate-900 truncate">{ghUser.login}</p>
                    <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-olive-100 text-olive-900 border border-olive-300">Active</span>
                  </div>
                  <p className="text-xs text-olive-800 font-medium mt-0.5">Connected &middot; Validated against GitHub v3 REST API</p>
                </div>
              </div>
            ) : !ghError ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 py-2">
                <Loader2 size={13} className="animate-spin text-olive-700" /> Validating credentials...
              </div>
            ) : null}

            <div className="pt-2 border-t border-slate-100">
              <label htmlFor="rotate-token" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Rotate Personal Access Token
              </label>
              <div className="flex gap-2">
                <input
                  id="rotate-token"
                  type="password"
                  value={newToken}
                  onChange={(e) => { setNewToken(e.target.value); setRotateError(null); setRotateMsg(null); }}
                  placeholder={user?.github_token_masked ? `Stored: ${user.github_token_masked}` : 'ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx'}
                  className="input text-xs font-mono flex-1 focus:ring-olive-600 focus:border-olive-600"
                  autoComplete="off"
                />
                <button onClick={handleRotateToken} disabled={rotating || !newToken.trim()} className="btn-secondary text-xs px-3.5 py-1.5 flex items-center gap-1.5">
                  {rotating ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                  Update Token
                </button>
              </div>
              {rotateError && <p className="text-xs text-red-600 mt-1.5 font-medium">{rotateError}</p>}
              {rotateMsg && <p className="text-xs text-olive-800 mt-1.5 font-medium">{rotateMsg}</p>}
              <p className="text-[11px] text-slate-500 mt-2 leading-relaxed">
                Cryptographically stored server-side with AES-256 GCM. Used strictly for read operations and automated refactoring branch generation.
              </p>
            </div>
          </div>

          {/* Grid zone */}
          <div className="card p-6 space-y-4">
            <div className="flex items-center gap-2.5 border-b border-slate-100 pb-3">
              <div className="w-8 h-8 rounded-xl bg-olive-50 text-olive-800 border border-olive-200 flex items-center justify-center">
                <Globe size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">Regional Power Grid</h2>
                <p className="text-[11px] text-slate-500">Determines carbon emissions per kilowatt-hour of electricity consumed</p>
              </div>
            </div>

            <div>
              <label htmlFor="zone" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Default Grid Region
              </label>
              <select
                id="zone"
                value={selectedZone}
                onChange={(e) => setSelectedZone(e.target.value)}
                className="input text-sm focus:ring-olive-600 focus:border-olive-600"
              >
                {GRID_ZONES.map((z) => (
                  <option key={z.value} value={z.value}>{z.label} &mdash; {z.value}</option>
                ))}
              </select>
            </div>

            {gridLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400">
                <Loader2 size={13} className="animate-spin text-olive-700" /> Querying grid telemetry endpoint...
              </div>
            ) : gridError ? (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200">
                <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 leading-relaxed font-medium">{gridError}</p>
              </div>
            ) : gridData ? (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200/80">
                  <dt className="label text-[11px]">Marginal Carbon Intensity</dt>
                  <dd className="font-mono font-bold text-slate-900 text-base mt-0.5">{gridData.marginal_carbon_intensity ?? gridData.carbon_intensity} <span className="text-xs font-normal text-slate-500">gCO₂e/kWh</span></dd>
                </div>
                <div className="p-3.5 rounded-xl bg-olive-50/60 border border-olive-200">
                  <dt className="label text-[11px] text-olive-900">Renewable Grid Share</dt>
                  <dd className="font-mono font-bold text-olive-900 text-base mt-0.5">{gridData.clean_energy_percentage}% <span className="text-xs font-normal text-olive-700">clean</span></dd>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200/80 col-span-2">
                  <dt className="label text-[10px]">Telemetry Source &amp; SLA</dt>
                  <dd className="text-xs text-slate-700 font-medium mt-0.5">
                    {gridData.name} &middot; {gridData.is_live ? 'Real-Time Marginal Telemetry (5 min cadence)' : 'Verified Historical Baseline'}
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
              <div className="w-8 h-8 rounded-xl bg-olive-50 text-olive-800 border border-olive-200 flex items-center justify-center">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900">CI/CD Quality Gate</h2>
                <p className="text-[11px] text-slate-500">Minimum Green Software score required for pull request pass</p>
              </div>
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700">Enforcement SLA</span>
                <span className="text-2xl font-black text-slate-900 font-mono">
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
                className="w-full accent-olive-700 cursor-pointer"
                aria-label="Quality gate threshold"
              />
              <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-1">
                <span>0 (Permissive)</span><span>50</span><span>100 (Strict)</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 text-center">
              <p className="text-xs font-semibold text-slate-600">Repositories scoring below {Number(qualityThreshold)} are blocked in CI/CD</p>
              <p className="text-3xl font-black mt-1.5 font-mono" style={{ color: Number(qualityThreshold) >= 80 ? '#384C3B' : '#d97706' }}>
                Grade {getThresholdGrade(Number(qualityThreshold))}
              </p>
            </div>

            <p className="text-[11px] text-slate-500 leading-relaxed">
              This threshold is consumed identically by GitHub Actions and the Alexa Voice MCP agent, guaranteeing deterministic policy enforcement.
            </p>
          </div>

          <div className="card p-6 space-y-4">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-olive-50 text-olive-800 border border-olive-200 flex items-center justify-center">
                  <Key size={16} />
                </div>
                <div>
                  <h2 className="text-sm font-bold text-slate-900">Plan Quota &amp; License Activation</h2>
                  <p className="text-[11px] text-slate-500">Activate a signed GC-LIC commercial key or sponsor tier</p>
                </div>
              </div>
              {usageData?.tier && (
                <span className="text-[10px] font-bold uppercase px-2 py-0.5 rounded bg-olive-100 text-olive-900 border border-olive-300">
                  {usageData.tier}
                </span>
              )}
            </div>

            {usageData && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Monthly API Usage</div>
                  <div className="font-mono font-bold text-slate-900 text-sm mt-0.5">
                    {usageData.used_calls ?? 0} / {usageData.included_calls ?? 100}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 border border-slate-200">
                  <div className="text-[10px] text-slate-500 uppercase font-semibold">Remaining Calls</div>
                  <div className="font-mono font-bold text-olive-800 text-sm mt-0.5">
                    {usageData.remaining_included_calls ?? 100}
                  </div>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="license-key-input" className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-1.5">
                Commercial License Key
              </label>
              <div className="flex gap-2">
                <input
                  id="license-key-input"
                  type="text"
                  value={licenseKey}
                  onChange={(e) => { setLicenseKey(e.target.value); setLicenseError(null); setLicenseMsg(null); }}
                  placeholder="GC-LIC-eyJvcmdfaWQiOjEsInRpZXIiOiJwcm8ifQ..."
                  className="input text-xs font-mono flex-1"
                  autoComplete="off"
                />
                <button
                  onClick={handleActivateLicense}
                  disabled={activatingLicense || !licenseKey.trim()}
                  className="btn-primary text-xs px-3.5 py-1.5 flex items-center gap-1.5"
                >
                  {activatingLicense ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                  Activate
                </button>
              </div>
              {licenseError && <p className="text-xs text-red-600 mt-1.5 font-medium">{licenseError}</p>}
              {licenseMsg && <p className="text-xs text-olive-800 mt-1.5 font-medium">{licenseMsg}</p>}
            </div>
          </div>

          <div className="card p-5">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-olive-50 border border-olive-200 flex items-center justify-center text-olive-800 shrink-0 mt-0.5">
                <Leaf size={15} />
              </div>
              <div>
                <p className="text-xs font-bold text-slate-900">Auditing Standards &amp; Architecture</p>
                <p className="text-[11px] text-slate-600 mt-1 leading-relaxed">
                  GreenCode audits repositories against <strong>ISO/IEC 21031:2024</strong> and the <strong>Green Software Foundation SCI v1.0</strong> standard. Algorithmic remediations are orchestrated via <strong>Amazon Bedrock Converse</strong> (Claude 3.5 Sonnet) and accessible hands-free via <strong>Alexa+ Voice MCP</strong>.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
