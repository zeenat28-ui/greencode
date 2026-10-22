import { useState, useEffect } from 'react';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { gridService, githubService, authService } from '../services/greencodeApi';
import { useAuth } from '../context/AuthContext';
import { ZoneData } from '../types';
import { GRID_ZONES } from '../styles/theme';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import {
  Globe, CheckCircle, ShieldCheck, Github, Loader2, RefreshCw,
  AlertCircle, Key, Leaf,
} from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import { authHeaders } from '../services/api';

function getThresholdGrade(val: number) {
  if (val >= 90) return 'A+';
  if (val >= 80) return 'A';
  if (val >= 70) return 'B';
  if (val >= 60) return 'C';
  return 'F';
}

export default function Settings() {
  const t = useT();
  const { user, refreshUser } = useAuth();

  const [selectedZone, setSelectedZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [qualityThreshold, setQualityThreshold] = useLocalStorage('greencode_threshold', 75);

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
      const headers = authHeaders();
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
      setLicenseError(t('settings.license.invalidFormat'));
      return;
    }
    setActivatingLicense(true);
    setLicenseError(null);
    setLicenseMsg(null);
    try {
      const headers = authHeaders({ 'Content-Type': 'application/json' });
      const res = await fetch('/api/billing/license/activate', {
        method: 'POST',
        headers,
        body: JSON.stringify({ org_id: 1, license_key: trimmed }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setLicenseError(body?.detail || t('settings.license.verificationFailed'));
      } else {
        setLicenseKey('');
        setLicenseMsg(t('settings.license.activated', { tier: String(body?.license?.tier || 'pro').toUpperCase(), seats: body?.license?.seats || 1 }));
        await loadBillingUsage();
      }
    } catch (err: any) {
      setLicenseError(err?.message || t('settings.license.reachError'));
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
      setGridError(err?.response?.data?.detail || t('settings.grid.reachError'));
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
        err?.response?.data?.detail || t('settings.github.invalidToken')
      );
    } finally {
      setGhTesting(false);
    }
  };

  useEffect(() => { testGitHub(); }, []);

  const handleRotateToken = async () => {
    const trimmed = newToken.trim();
    if (!trimmed) {
      setRotateError(t('settings.github.pasteToken'));
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
      setRotateMsg(t('settings.github.tokenUpdated'));
    } catch (err: any) {
      setRotateError(err?.response?.data?.detail || t('settings.github.tokenRejected'));
    } finally {
      setRotating(false);
    }
  };

  return (
    <div className="space-y-5">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-zinc-200/80 dark:border-slate-700 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 tracking-tight">{t('settings.title')}</h1>
            <Badge variant="olive">{t('settings.badge')}</Badge>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            {t('settings.subtitle')}
          </p>
        </div>
        <div className="flex items-center gap-2.5">
          <span
            className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-800 dark:text-emerald-300 bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 px-3 py-1.5 rounded-lg"
            title={t('settings.autoSaveTitle')}
          >
            <CheckCircle size={13} className="text-emerald-600" /> {t('settings.autoSaved')}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 items-start">
        <div className="lg:col-span-7 space-y-5">
          {/* GitHub connection */}
          <Card padding="lg" className="space-y-4 dark:bg-slate-900 dark:border-slate-700">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-slate-700 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-zinc-900 text-white flex items-center justify-center">
                  <Github size={15} />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{t('settings.github.title')}</h2>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">{t('settings.github.subtitle')}</p>
                </div>
              </div>
              <Button onClick={testGitHub} disabled={ghTesting} variant="secondary" size="sm" className="text-xs">
                {ghTesting ? <Loader2 size={11} className="animate-spin text-emerald-600" /> : <RefreshCw size={11} />}
                {t('settings.github.testButton')}
              </Button>
            </div>

            {ghError && (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-red-50 border border-red-200 dark:border-red-800">
                <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                <p className="text-xs text-red-700 dark:text-red-300 leading-relaxed font-medium">{ghError}</p>
              </div>
            )}

            {ghUser ? (
              <div className="flex items-center gap-3 p-3.5 rounded-xl bg-emerald-50/60 border border-emerald-200">
                {ghUser.avatar_url && <img src={ghUser.avatar_url} alt="" className="w-9 h-9 rounded-full border border-emerald-300" />}
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100 truncate">{ghUser.login}</p>
                    <Badge variant="olive">{t('settings.github.active')}</Badge>
                  </div>
                  <p className="text-[11px] text-emerald-800 dark:text-emerald-300 mt-0.5">{t('settings.github.verifiedVia')}</p>
                </div>
              </div>
            ) : !ghError ? (
              <div className="flex items-center gap-2 text-xs text-zinc-400 dark:text-zinc-500 py-2">
                <Loader2 size={13} className="animate-spin text-emerald-600" /> {t('settings.github.validating')}
              </div>
            ) : null}

            <div className="pt-2 border-t border-zinc-100">
              <label htmlFor="rotate-token" className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
                {t('settings.github.rotateToken')}
              </label>
              <div className="flex gap-2">
                <Input
                  id="rotate-token"
                  type="password"
                  value={newToken}
                  onChange={(e) => { setNewToken(e.target.value); setRotateError(null); setRotateMsg(null); }}
                  placeholder={user?.github_token_masked ? `Stored: ${user.github_token_masked}` : t('settings.github.tokenPlaceholder')}
                  className="text-xs font-mono flex-1"
                  autoComplete="off"
                />
                <Button onClick={handleRotateToken} disabled={rotating || !newToken.trim()} variant="secondary" size="sm" className="text-xs">
                  {rotating ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                  {t('settings.github.updateToken')}
                </Button>
              </div>
              {rotateError && <p className="text-xs text-red-600 mt-1.5 font-medium">{rotateError}</p>}
              {rotateMsg && <p className="text-xs text-emerald-800 mt-1.5 font-medium">{rotateMsg}</p>}
              <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-2 leading-relaxed">
                {t('settings.github.tokenNote')}
              </p>
            </div>
          </Card>

        {/* Grid zone */}
        <Card padding="lg" className="space-y-4 dark:bg-slate-900 dark:border-slate-700">
          <div className="flex items-center gap-2.5 border-b border-slate-100 dark:border-slate-700 pb-3">
            <div className="w-8 h-8 rounded-xl bg-olive-50 dark:bg-olive-900/20 text-olive-800 dark:text-olive-300 border border-olive-200 dark:border-olive-800 flex items-center justify-center">
              <Globe size={16} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t('settings.grid.title')}</h2>
              <p className="text-[11px] text-slate-500 dark:text-slate-400">{t('settings.grid.subtitle')}</p>
            </div>
          </div>

          <div>
            <label htmlFor="zone" className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300 mb-1.5">
              {t('settings.grid.regionLabel')}
            </label>
            <Select
              id="zone"
              value={selectedZone}
              onChange={(e) => setSelectedZone(e.target.value)}
              className="text-sm focus:ring-olive-600 focus:border-olive-600"
            >
              {GRID_ZONES.map((z) => (
                <option key={z.value} value={z.value}>{z.label} &mdash; {z.value}</option>
              ))}
            </Select>
          </div>

            {gridLoading ? (
              <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500">
                <Loader2 size={13} className="animate-spin text-olive-700" /> {t('settings.grid.querying')}
              </div>
            ) : gridError ? (
              <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-50 border border-amber-200 dark:border-amber-800">
                <AlertCircle size={14} className="text-amber-500 shrink-0 mt-0.5" />
                <p className="text-xs text-amber-800 dark:text-amber-300 leading-relaxed font-medium">{gridError}</p>
              </div>
            ) : gridData ? (
              <dl className="grid grid-cols-2 gap-3 text-sm">
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                  <dt className="label text-[11px] text-slate-500 dark:text-slate-400">{t('settings.grid.carbonIntensity')}</dt>
                  <dd className="font-mono font-bold text-slate-900 dark:text-slate-100 text-base mt-0.5">{gridData.marginal_carbon_intensity ?? gridData.carbon_intensity} <span className="text-xs font-normal text-slate-500 dark:text-slate-400">gCO₂e/kWh</span></dd>
                </div>
                <div className="p-3.5 rounded-xl bg-olive-50/60 dark:bg-olive-900/20 border border-olive-200 dark:border-olive-800">
                  <dt className="label text-[11px] text-olive-900 dark:text-olive-300">{t('settings.grid.renewableShare')}</dt>
                  <dd className="font-mono font-bold text-olive-900 dark:text-olive-300 text-base mt-0.5">{gridData.clean_energy_percentage}% <span className="text-xs font-normal text-olive-700 dark:text-olive-400">{t('settings.grid.clean')}</span></dd>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 col-span-2">
                  <dt className="label text-[10px] text-slate-500 dark:text-slate-400">{t('settings.grid.telemetry')}</dt>
                  <dd className="text-xs text-slate-700 dark:text-slate-300 font-medium mt-0.5">
                    {gridData.name} &middot; {gridData.is_live ? t('settings.grid.realTime') : t('settings.grid.historical')}
                  </dd>
                </div>
              </dl>
              ) : null}
          </Card>
        </div>

        {/* Quality gate */}
        <div className="lg:col-span-5 space-y-5">
          <Card padding="lg" className="space-y-4 dark:bg-slate-900 dark:border-slate-700">
            <div className="flex items-center gap-2.5 border-b border-slate-100 dark:border-slate-700 pb-3">
              <div className="w-8 h-8 rounded-xl bg-olive-50 dark:bg-olive-900/20 text-olive-800 dark:text-olive-300 border border-olive-200 dark:border-olive-800 flex items-center justify-center">
                <ShieldCheck size={16} />
              </div>
              <div>
                <h2 className="text-sm font-bold text-slate-900 dark:text-slate-100">{t('settings.gate.title')}</h2>
                <p className="text-[11px] text-slate-500 dark:text-slate-400">{t('settings.gate.subtitle')}</p>
              </div>
            </div>

            <div>
              <div className="flex items-baseline justify-between mb-2">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">{t('settings.gate.enforcementSla')}</span>
                <span className="text-2xl font-black text-slate-900 dark:text-slate-100 font-mono">
                  {Number(qualityThreshold)}
                  <span className="text-xs font-semibold text-slate-400 dark:text-slate-500 ml-1">/ 100</span>
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
                aria-label={t('settings.gate.thresholdAria')}
              />
              <div className="flex justify-between text-[10px] text-slate-400 dark:text-slate-500 font-mono mt-1">
                <span>{t('settings.gate.permissive')}</span><span>50</span><span>{t('settings.gate.strict')}</span>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-zinc-50 dark:bg-zinc-800/50 border border-zinc-200 dark:border-zinc-700 text-center">
              <p className="text-xs text-zinc-600 dark:text-zinc-400">{t('settings.gate.blockedBelow', { threshold: Number(qualityThreshold) })}</p>
              <p className="text-2xl font-bold mt-1 font-mono" style={{ color: Number(qualityThreshold) >= 80 ? '#059669' : '#d97706' }}>
                {t('settings.gate.grade', { grade: getThresholdGrade(Number(qualityThreshold)) })}
              </p>
            </div>

            <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-relaxed">
              {t('settings.gate.enforcedAcross')}
            </p>
          </Card>

          <Card padding="lg" className="space-y-4 dark:bg-slate-900 dark:border-slate-700">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-slate-700 pb-3">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-800 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center">
                  <Key size={15} />
                </div>
                <div>
                  <h2 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">{t('settings.license.title')}</h2>
                  <p className="text-[11px] text-zinc-500 dark:text-zinc-400">{t('settings.license.subtitle')}</p>
                </div>
              </div>
              {usageData?.tier && (
                <Badge variant="olive" className="uppercase">
                  {usageData.tier}
                </Badge>
              )}
            </div>

            {usageData && (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] text-zinc-500 uppercase font-semibold">Monthly API Usage</div>
                  <div className="font-mono font-bold text-zinc-900 text-sm mt-0.5">
                    {usageData.used_calls ?? 0} / {usageData.included_calls ?? 100}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-200">
                  <div className="text-[10px] text-zinc-500 uppercase font-semibold">Remaining Calls</div>
                  <div className="font-mono font-bold text-emerald-700 text-sm mt-0.5">
                    {usageData.remaining_included_calls ?? 100}
                  </div>
                </div>
              </div>
            )}

            <div>
              <label htmlFor="license-key-input" className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1.5">
                {t('settings.license.keyLabel')}
              </label>
              <div className="flex gap-2">
                <Input
                  id="license-key-input"
                  type="text"
                  value={licenseKey}
                  onChange={(e) => { setLicenseKey(e.target.value); setLicenseError(null); setLicenseMsg(null); }}
                  placeholder={t('settings.license.keyPlaceholder')}
                  className="text-xs font-mono flex-1"
                  autoComplete="off"
                />
              <Button
                onClick={handleActivateLicense}
                disabled={activatingLicense || !licenseKey.trim()}
                variant="primary"
                size="sm"
                className="text-xs"
              >
                {activatingLicense ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />}
                {t('settings.license.activateButton')}
              </Button>
              </div>
              {licenseError && <p className="text-xs text-red-600 mt-1.5 font-medium">{licenseError}</p>}
              {licenseMsg && <p className="text-xs text-emerald-800 mt-1.5 font-medium">{licenseMsg}</p>}
            </div>
          </Card>

          <Card padding="lg">
            <div className="flex items-start gap-3">
              <div className="w-7 h-7 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800 flex items-center justify-center text-emerald-700 dark:text-emerald-300 shrink-0 mt-0.5">
                <Leaf size={14} />
              </div>
              <div>
                <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">{t('settings.standards.title')}</p>
                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-1 leading-relaxed">
                  Audits conform to ISO/IEC 21031:2024 (GSF SCI v1.0), FinOps FOCUS 1.4, and OpenTelemetry OTLP/HTTP v1.
                </p>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}
