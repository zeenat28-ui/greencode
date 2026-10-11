import React, { useState, useEffect } from 'react';
import { Download, ShieldCheck, ExternalLink, FileSpreadsheet, Archive, RefreshCw } from 'lucide-react';

export default function Reports() {
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
        fetch('/api/reports/esg/1'),
        fetch('/api/reports/esg/1/evidence-manifest'),
        fetch('/api/reports/compliance/1'),
        fetch('/api/reports/audit-logs/1?limit=8'),
        fetch('/api/reports/impact-framework-manifest'),
      ]);
      if (esgRes.ok) setEsgData(await esgRes.json());
      if (manRes.ok) setManifestData(await manRes.json());
      if (compRes.ok) setComplianceData(await compRes.json());
      if (logsRes.ok) {
        const lJson = await logsRes.json();
        setAuditLogs(Array.isArray(lJson?.entries) ? lJson.entries : []);
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
      const res = await fetch('/api/reports/audit-logs/1/verify');
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900">ESG Disclosures &amp; Audit Assurance</h1>
          <p className="text-sm text-slate-500">
            Corporate sustainability reporting conforming to SEC, CSRD ESRS E1, ISO 14064-1, and GHG Protocol
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={loadReportsData}
            disabled={loading}
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium px-3 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </button>
          <a
            href="/api/reports/esg/1/evidence-bundle"
            className="bg-slate-900 hover:bg-slate-800 text-white font-medium px-3.5 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Archive className="w-3.5 h-3.5" /> Signed CSRD Bundle (.zip)
          </a>
          <a
            href="/api/reports/esg/1/export/html"
            target="_blank"
            rel="noreferrer"
            className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-3.5 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors shadow-sm"
          >
            <Download className="w-3.5 h-3.5" /> HTML Report
          </a>
          <a
            href="/api/reports/esg/1/csv"
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium px-3.5 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
          >
            <FileSpreadsheet className="w-3.5 h-3.5" /> CSV
          </a>
          <a
            href="/api/reports/esg/1"
            target="_blank"
            rel="noreferrer"
            className="bg-slate-100 hover:bg-slate-200 text-slate-800 font-medium px-3.5 py-2 rounded-lg text-xs flex items-center gap-1.5 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" /> SEC JSON
          </a>
        </div>
      </div>

      {/* Cryptographic Ledger Assurance Card */}
      <div className="bg-slate-900 border border-slate-800 text-white rounded-xl p-6 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            <h2 className="font-semibold text-base text-white">Cryptographic SHA-256 Audit Trail &amp; Evidence Manifest</h2>
          </div>
          <p className="text-xs text-slate-400">
            Every policy rule, workload rollback, and PR gate decision is hash-chained to provide tamper-evident proof to auditors.
          </p>
          {manifestData?.bundle_root_sha256 && (
            <p className="text-[11px] font-mono text-emerald-400 pt-1">
              Bundle Root SHA-256: {manifestData.bundle_root_sha256}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {integrityData && (
            <span className="text-xs font-semibold px-3 py-1.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              {integrityData.status || (integrityData.valid ? 'VERIFIED' : 'INVALID')} ({integrityData.checked_records ?? 0} entries)
            </span>
          )}
          <button
            onClick={verifyAuditLedger}
            disabled={verifying}
            className="bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-medium px-4 py-2 rounded-lg text-sm transition-colors"
          >
            {verifying ? 'Verifying Chain...' : 'Verify Cryptographic Chain'}
          </button>
        </div>
      </div>

      {/* Scope 2 & Scope 3 Breakdown */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-200 flex flex-wrap justify-between items-center gap-2">
          <div>
            <h2 className="font-semibold text-slate-900">Emissions Inventory by Accounting Standard</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Organization: <strong>{esgData?.organization_name || 'Organization-1'}</strong> &middot; Provenance: <span className="font-mono">{esgData?.data_provenance || 'calibrated_instance_model'}</span>
            </p>
          </div>
          {esgData?.reporting_period && (
            <span className="text-xs text-emerald-700 font-semibold bg-emerald-50 px-2.5 py-1 rounded-full">
              Period: {esgData.reporting_period} ({esgData?.assurance_verdict?.status || 'MODELED'})
            </span>
          )}
        </div>
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500 text-xs uppercase border-b border-slate-200">
            <tr>
              <th className="px-5 py-3.5">Category</th>
              <th className="px-5 py-3.5">Standard</th>
              <th className="px-5 py-3.5">Calculated Footprint</th>
              <th className="px-5 py-3.5">Financial Impact</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            <tr>
              <td className="px-5 py-4 font-semibold text-slate-900">Cloud Compute (Scope 2)</td>
              <td className="px-5 py-4 text-slate-600">GHG Protocol Market-Based</td>
              <td className="px-5 py-4 font-medium font-mono text-slate-900">
                {scope2Tonnes} tCO2e ({totalKwh} kWh)
              </td>
              <td className="px-5 py-4 font-mono text-slate-600">${operationalCostUsd} USD</td>
            </tr>
            <tr>
              <td className="px-5 py-4 font-semibold text-slate-900">Embodied Hardware (Scope 3)</td>
              <td className="px-5 py-4 text-slate-600">GSF SCI v1.0 Hardware Factor</td>
              <td className="px-5 py-4 font-medium font-mono text-slate-900">
                {scope3Tonnes} tCO2e
              </td>
              <td className="px-5 py-4 text-slate-600">Amortized Infrastructure</td>
            </tr>
            <tr className="bg-emerald-50/50">
              <td className="px-5 py-4 font-bold text-emerald-800">Avoided Emissions (GreenCode)</td>
              <td className="px-5 py-4 text-emerald-700 font-medium">Pre/Post AST Diff Verified</td>
              <td className="px-5 py-4 font-bold font-mono text-emerald-700">
                -{avoidedTonnes} tCO2e
              </td>
              <td className="px-5 py-4 font-bold font-mono text-emerald-700">
                -${savingsUsd} USD saved / mo
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Compliance Posture & Recent Hash-Chained Audit Trail */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h3 className="font-semibold text-slate-900 text-sm">Security &amp; Regulatory Posture</h3>
            {complianceData?.overall_status && (
              <span className="text-xs font-bold px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
                {complianceData.overall_status}
              </span>
            )}
          </div>
          <ul className="space-y-2 text-xs text-slate-600">
            {(esgData?.standards_compliance || []).map((std: string, idx: number) => (
              <li key={idx} className="flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
                <span>{std}</span>
              </li>
            ))}
          </ul>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex justify-between items-center border-b border-slate-100 pb-3">
            <h3 className="font-semibold text-slate-900 text-sm">Recent Hash-Chained Audit Ledger</h3>
            <span className="text-xs font-mono text-slate-500">{auditLogs.length} recent events</span>
          </div>
          {auditLogs.length === 0 ? (
            <p className="text-xs text-slate-500 py-4">No audit trail events recorded yet.</p>
          ) : (
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
              {auditLogs.map((entry: any) => (
                <div key={entry.id} className="p-2.5 rounded-lg bg-slate-50 border border-slate-200 text-xs flex justify-between items-center gap-2">
                  <div>
                    <div className="font-semibold text-slate-800">{entry.action}</div>
                    <div className="text-[11px] text-slate-500 font-mono truncate max-w-xs">
                      {entry.resource} &middot; {String(entry.record_hash || '').slice(0, 16)}...
                    </div>
                  </div>
                  <span className="text-[10px] font-mono text-slate-400 shrink-0">
                    {entry.timestamp ? new Date(entry.timestamp).toLocaleTimeString() : ''}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Green Software Foundation Impact Framework (.imp.yaml) Manifest */}
      {ifManifest && (
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm space-y-3">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 border-b border-slate-100 pb-3">
            <div>
              <h3 className="font-semibold text-slate-900 text-sm">
                Green Software Foundation Impact Framework (.imp.yaml) Manifest
              </h3>
              <p className="text-xs text-slate-500">
                Standardized @grnsft/if-plugins pipeline (SciE, SciO, SciM, Sci) conforming to ISO/IEC 21031:2024
              </p>
            </div>
            <a
              href="/api/reports/impact-framework-manifest"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-medium px-3 py-1.5 rounded-lg bg-slate-900 text-white hover:bg-slate-800 transition-colors"
            >
              Open IF Manifest JSON
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



