import React, { useState, useEffect } from 'react';
import { Download, ShieldCheck, ExternalLink, FileSpreadsheet, Archive, RefreshCw } from 'lucide-react';
import { useT } from '../i18n/I18nContext';
import { authHeaders } from '../services/api';

export default function Reports() {
  const t = useT();
  const [integrityData, setIntegrityData] = useState<any>(null);
  const [verifying, setVerifying] = useState(false);
  const [esgData, setEsgData] = useState<any>(null);
  const [manifestData, setManifestData] = useState<any>(null);
  const [complianceData, setComplianceData] = useState<any>(null);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [ifManifest, setIfManifest] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadReportsData = async () => {
    setLoading(true);
    try {
      const [esgRes, manRes, compRes, logsRes, ifRes] = await Promise.all([
        fetch('/api/reports/esg/1', { headers: authHeaders() }),
        fetch('/api/reports/esg/1/evidence-manifest', { headers: authHeaders() }),
        fetch('/api/reports/compliance/1', { headers: authHeaders() }),
        fetch('/api/reports/audit-logs/1?limit=8', { headers: authHeaders() }),
        fetch('/api/reports/impact-framework-manifest', { headers: authHeaders() }),
      ]);
      if (esgRes.ok) setEsgData(await esgRes.json());
      if (manRes.ok) setManifestData(await manRes.json());
      if (compRes.ok) setComplianceData(await compRes.json());
      if (logsRes.ok) {
        // The audit trail endpoint returns a bare JSON array of ledger entries.
        const lJson = await logsRes.json();
        setAuditLogs(Array.isArray(lJson) ? lJson : (lJson?.entries ?? []));
      }
      if (ifRes.ok) setIfManifest(await ifRes.json());
    } catch {
      // Non-blocking
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadReportsData();
  }, []);

  const verifyAuditLedger = async () => {
    setVerifying(true);
    try {
      const res = await fetch('/api/reports/audit-logs/1/verify', { headers: authHeaders() });
      if (res.ok) {
        setIntegrityData(await res.json());
      }
    } catch {
      // Non-blocking
    } finally {
      setVerifying(false);
    }
  };

  const summary = esgData?.emissions_summary || {};
  const scope2Tonnes = summary.scope_2_cloud_operational_tco2e ?? esgData?.scope_2_tonnes_co2e ?? 0;
  const scope3Tonnes = summary.scope_3_embodied_infrastructure_tco2e ?? esgData?.scope_3_tonnes_co2e ?? 0;
  const totalKwh = summary.total_energy_consumption_kwh ?? 0;
  const avoidedTonnes = summary.avoided_carbon_emissions_tco2e ?? 0;
  const savingsUsd = summary.financial_cloud_savings_usd ?? 0;
  const operationalCostUsd = Number((totalKwh * 0.12).toFixed(2));

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-3 border-b border-zinc-200/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 tracking-tight">{t('reports.title')}</h1>
            <span className="badge-olive">SHA-256 Ledger</span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            {t('reports.subtitle')}
          </p>
        </div>
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={loadReportsData}
            disabled={loading}
            className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> {t('reports.refresh')}
          </button>
          <a
            href="/api/reports/esg/1/evidence-bundle"
            className="btn-primary text-xs px-3 py-1.5 flex items-center gap-1.5"
          >
            <Archive className="w-3.5 h-3.5" /> {t('reports.signedBundle')}
          </a>
          <a
            href="/api/reports/esg/1/export/html"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5 text-emerald-600" /> {t('reports.htmlReport')}
          </a>
          <a
            href="/api/reports/esg/1/csv"
            className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" /> {t('reports.csv')}
          </a>
          <a
            href="/api/reports/esg/1"
            target="_blank"
            rel="noreferrer"
            className="btn-secondary text-xs px-2.5 py-1.5 flex items-center gap-1.5"
          >
            <ExternalLink className="w-3.5 h-3.5" /> {t('reports.json')}
          </a>
        </div>
      </div>

      {/* Cryptographic Ledger Assurance Card */}
        <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-emerald-400" />
              <h2 className="font-semibold text-base text-white">{t('reports.cryptoLedger')}</h2>
            </div>
            <p className="text-xs text-slate-400 dark:text-slate-500">
              {t('reports.ledgerDesc')}
            </p>
          {manifestData?.bundle_root_sha256 && (
            <p className="text-[11px] font-mono text-emerald-400 pt-1">
              {t('reports.bundleRoot')}: {manifestData.bundle_root_sha256}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {integrityData && (
            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {integrityData.status || (integrityData.valid ? t('reports.valid') : t('reports.invalid'))} ({integrityData.records_verified ?? 0} {t('reports.entries')})
            </span>
          )}
          <button
            onClick={verifyAuditLedger}
            disabled={verifying}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium px-4 py-2 rounded-lg text-sm transition-colors"
          >
            {verifying ? t('reports.verifying') : t('reports.verifyChain')}
          </button>
        </div>
      </div>

      {/* Scope 2 & Scope 3 Breakdown */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl overflow-hidden shadow-sm">
          <div className="p-5 border-b border-slate-200 dark:border-slate-700 flex flex-wrap justify-between items-center gap-2">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100">{t('reports.emissionsInventory')}</h2>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                {t('reports.organization')}: <strong>{esgData?.organization_name || 'Organization-1'}</strong> &middot; {t('reports.provenance')}: <span className="font-mono">{esgData?.data_provenance || 'calibrated_instance_model'}</span>
              </p>
          </div>
          {esgData?.reporting_period && (
            <span className="text-xs text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full">
              {t('reports.period', { period: esgData.reporting_period, status: esgData?.assurance_verdict?.status || 'MODELED' })}
            </span>
          )}
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 dark:bg-slate-800 text-slate-500 dark:text-slate-400 text-xs uppercase border-b border-slate-200 dark:border-slate-700">
            <tr>
              <th className="px-5 py-3.5">{t('reports.table.category')}</th>
              <th className="px-5 py-3.5">{t('reports.table.standard')}</th>
              <th className="px-5 py-3.5">{t('reports.table.footprint')}</th>
              <th className="px-5 py-3.5">{t('reports.table.financial')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
            <tr>
              <td className="px-5 py-4 font-semibold text-slate-900 dark:text-slate-100">{t('reports.scope2')}</td>
              <td className="px-5 py-4 text-slate-600 dark:text-slate-400">{t('reports.ghgProtocol')}</td>
              <td className="px-5 py-4 font-medium font-mono text-slate-900 dark:text-slate-200">
                {scope2Tonnes} tCO2e ({totalKwh} kWh)
              </td>
              <td className="px-5 py-4 font-mono text-slate-600 dark:text-slate-400">${operationalCostUsd} USD</td>
            </tr>
            <tr>
              <td className="px-5 py-4 font-semibold text-slate-900 dark:text-slate-100">{t('reports.scope3')}</td>
              <td className="px-5 py-4 text-slate-600 dark:text-slate-400">{t('reports.sciHardware')}</td>
              <td className="px-5 py-4 font-medium font-mono text-slate-900 dark:text-slate-200">
                {scope3Tonnes} tCO2e
              </td>
              <td className="px-5 py-4 text-slate-600 dark:text-slate-400">{t('reports.amortizedInfra')}</td>
            </tr>
            <tr className="bg-emerald-50/50 dark:bg-emerald-900/20">
              <td className="px-5 py-4 font-bold text-emerald-800 dark:text-emerald-300">{t('reports.avoidedEmissions')}</td>
              <td className="px-5 py-4 text-emerald-700 dark:text-emerald-300 font-medium">{t('reports.astVerified')}</td>
              <td className="px-5 py-4 font-bold font-mono text-emerald-700 dark:text-emerald-300">
                -{avoidedTonnes} tCO2e
              </td>
              <td className="px-5 py-4 font-bold font-mono text-emerald-700 dark:text-emerald-300">
                -${savingsUsd} {t('reports.savedPerMo')}
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Compliance Posture & Recent Hash-Chained Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-700 pb-3">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">{t('reports.compliancePosture')}</h3>
            {complianceData?.overall_status && (
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-900/20 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800">
                {complianceData.overall_status}
              </span>
            )}
          </div>
          <ul className="space-y-2 text-xs text-slate-600 dark:text-slate-400">
            {(esgData?.standards_compliance || []).map((std: string, idx: number) => (
              <li key={idx} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span>{std}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 dark:border-slate-700 pb-3">
            <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">{t('reports.auditLedger')}</h3>
            <span className="text-xs font-mono text-slate-500 dark:text-slate-400">{auditLogs.length} {t('reports.recentEvents')}</span>
          </div>
          {auditLogs.length === 0 ? (
            <p className="text-xs text-slate-500 dark:text-slate-400 py-4">{t('reports.noAuditTrail')}</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {auditLogs.map((entry: any) => (
                <div key={entry.id} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs flex justify-between items-center gap-2">
                  <div>
                    <div className="font-semibold text-slate-800 dark:text-slate-200">{entry.action}</div>
                    <div className="text-[11px] text-slate-500 dark:text-slate-400 font-mono truncate max-w-xs">
                      {entry.resource_type || entry.resource || 'audit'} &middot; {String(entry.record_hash || entry.details?.record_hash || '').slice(0, 16)}...
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 dark:text-slate-500 shrink-0">
                    {entry.created_at || entry.timestamp
                      ? new Date(entry.created_at || entry.timestamp).toLocaleTimeString()
                      : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Green Software Foundation Impact Framework (.imp.yaml) Manifest */}
      {ifManifest && (
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 dark:border-slate-700 pb-3">
            <div>
              <h3 className="font-semibold text-slate-900 dark:text-slate-100 text-sm">
                {t('reports.ifManifest.title')}
              </h3>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('reports.ifManifest.description')}
              </p>
            </div>
            <a
              href="/api/reports/impact-framework-manifest"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              {t('reports.ifManifest.openJson')}
            </a>
          </div>
          <pre className="bg-slate-900 text-emerald-300 font-mono text-xs p-4 rounded-lg overflow-x-auto max-h-56">
            {ifManifest.yaml_manifest}
          </pre>
        </div>
      )}
    </div>
  );
}



