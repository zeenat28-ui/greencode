import { useState } from 'react';
import { 
  FileText, Printer, Copy, Check, X, ShieldCheck, 
  Leaf, Zap, DollarSign, Award
} from 'lucide-react';
import { ScanResult } from '../../types';
import { Modal } from '../primitives/Modal';
import { translateStatic as t } from '../../i18n/I18nContext';

interface EsgAuditModalProps {
  isOpen: boolean;
  onClose: () => void;
  scanData: ScanResult;
  activeZone?: string;
  marginalRate?: number | null;
}

export default function EsgAuditModal({
  isOpen,
  onClose,
  scanData,
  activeZone = 'US-CAL-CISO',
  marginalRate = 215,
}: EsgAuditModalProps) {
  const [copied, setCopied] = useState(false);

  const score = scanData.green_score ?? 0;
  const violations = scanData.total_violations ?? 0;
  const energyWh = scanData.energy_wh ?? 0;
  const carbonG = scanData.carbon_g ?? (energyWh / 1000) * (marginalRate ?? 0);
  const auditDate = new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
  const auditId = `GC-ESG-${String(scanData.total_files || 0).padStart(4, '0')}-${score}-${new Date().getFullYear()}`;

  // Modeled annual projection: each detected violation is assumed to represent
  // ~1.8 W of continuous CPU draw running 24/7 (8,760 h). Dollar savings derive
  // from the resulting kWh at a stated ~$0.12/kWh grid rate — no per-violation
  // dollar figure is invented. The disclosure below states these are estimates.
  const annualKwhSaved = ((violations * 1.8 * 8760) / 1000);
  const annualKgCo2Saved = ((annualKwhSaved * (marginalRate ?? 0)) / 1000);
  const annualDollarSaved = Math.round(annualKwhSaved * 0.12);

  const handlePrint = () => {
    window.print();
  };

  const handleCopyJson = () => {
    const reportData = {
      standard: "Green Software Foundation Software Carbon Intensity (GSF SCI v1.0)",
      complianceStatus: score >= 75 ? "PASSED" : "ACTION_REQUIRED",
      auditCertificateId: auditId,
      auditTimestamp: new Date().toISOString(),
      repository: scanData.repo_path,
      sciScore: score,
      metrics: {
        operationalEnergyWh: energyWh,
        carbonGrams: carbonG,
        gridIntensityZone: activeZone,
        gridMarginalRate: marginalRate,
        totalSourceFiles: scanData.total_files || 0,
        totalLinesOfCode: scanData.total_lines || 0,
        algorithmicBottlenecks: violations,
      },
      projections: {
        annualKwhSaved,
        annualKgCo2Saved,
        annualEstimatedDollarSavings: annualDollarSaved,
      },
      verificationProof: "Intel/AMD RAPL hardware sensor baseline comparison (app/pipeline/verifier.py)",
    };

    navigator.clipboard.writeText(JSON.stringify(reportData, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      showCloseButton={false}
      size="lg"
      overlayClassName="items-center bg-slate-900/60 print:p-0 print:bg-white"
      className="!max-w-3xl border-slate-200 overflow-hidden print:border-none print:shadow-none print:max-w-full"
      contentClassName="p-0 overflow-visible"
    >
        {/* Modal Action Bar (Hidden when printing) */}
        <div className="bg-slate-900 text-white px-6 py-3.5 flex items-center justify-between print:hidden">
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-300">
            <FileText size={15} className="text-olive-400" />
            {t('modals.esg.actionBar')}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyJson}
              className="btn-secondary text-xs px-2.5 py-1 bg-slate-800 text-slate-200 border-slate-700 hover:bg-slate-700 flex items-center gap-1.5"
            >
              {copied ? <Check size={12} className="text-emerald-400" /> : <Copy size={12} />}
              {copied ? t('modals.esg.copiedJson') : t('modals.esg.copyJson')}
            </button>
            <button
              onClick={handlePrint}
              className="btn-primary text-xs px-3 py-1 flex items-center gap-1.5 bg-olive-700 hover:bg-olive-800"
            >
              <Printer size={12} />
              {t('modals.esg.printPdf')}
            </button>
            <button
              onClick={onClose}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 ml-2"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        {/* Printable Audit Document */}
        <div className="p-8 space-y-6 text-slate-800 print:p-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 border-b border-slate-200 pb-5">
            <div>
              <div className="flex items-center gap-2 text-olive-800 font-bold tracking-tight text-lg">
                <Leaf size={20} className="text-olive-700" />
                {t('modals.esg.reportTitle')}
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                {t('modals.esg.reportSubtitle')}
              </p>
            </div>
            <div className="text-right sm:text-right font-mono text-xs text-slate-500">
              <div>{t('modals.esg.certificate', { auditId })}</div>
              <div>{t('modals.esg.date', { date: auditDate })}</div>
              <div className="mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-olive-50 text-olive-800 border border-olive-200">
                <ShieldCheck size={12} />
                {t('modals.esg.badge')}
              </div>
            </div>
          </div>

          {/* Repo & Executive Verdict */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="md:col-span-2 p-4 rounded-lg bg-slate-50 border border-slate-200 space-y-2">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                {t('modals.esg.auditedScope')}
              </div>
              <div className="font-mono text-sm font-bold text-slate-900 truncate">
                {scanData.repo_path || t('modals.esg.repositoryCodebase')}
              </div>
              <div className="text-xs text-slate-600 flex flex-wrap gap-x-4 gap-y-1">
                <span>{t('modals.esg.filesAudited')}: <strong className="text-slate-800">{scanData.total_files || 0}</strong></span>
                <span>{t('modals.esg.codeScale')}: <strong className="text-slate-800">{(scanData.total_lines || 0).toLocaleString()} LOC</strong></span>
                <span>{t('modals.esg.gridZone')}: <strong className="text-slate-800">{activeZone}</strong></span>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-olive-50/70 border border-olive-200 flex flex-col justify-center items-center text-center">
              <div className="text-[11px] font-bold uppercase tracking-wider text-olive-900 mb-1">
                {t('modals.esg.sciScore')}
              </div>
              <div className="text-3xl font-black text-olive-800 font-mono">
                {score}<span className="text-sm font-normal text-slate-500">/100</span>
              </div>
              <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 mt-1 rounded bg-olive-100 text-olive-900 border border-olive-300">
                {score >= 80 ? t('modals.esg.gradeA') : score >= 65 ? t('modals.esg.gradeB') : t('modals.esg.gradeC')}
              </span>
            </div>
          </div>

          {/* Core Metrics Table */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-2">
              {t('modals.esg.sciBreakdown')}
            </h4>
            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold text-left">
                  <tr>
                    <th className="py-2 px-3">{t('modals.esg.metricParameter')}</th>
                    <th className="py-2 px-3">{t('modals.esg.measurementStandard')}</th>
                    <th className="py-2 px-3 text-right">{t('modals.esg.value')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 font-mono">
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{t('modals.esg.operationalEnergy')}</td>
                    <td className="py-2.5 px-3 font-sans text-slate-500">{t('modals.esg.operationalEnergyStandard')}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">{(energyWh * 1000).toFixed(2)} mWh / op</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{t('modals.esg.marginalGridCarbon')}</td>
                    <td className="py-2.5 px-3 font-sans text-slate-500">{t('modals.esg.marginalGridCarbonStandard', { zone: activeZone })}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">{marginalRate ?? '—'} {marginalRate != null && 'gCO₂e/kWh'}</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{t('modals.esg.totalOperationalCarbon')}</td>
                    <td className="py-2.5 px-3 font-sans text-slate-500">{t('modals.esg.totalOperationalCarbonStandard')}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">{carbonG.toFixed(4)} gCO₂e</td>
                  </tr>
                  <tr>
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-800">{t('modals.esg.antiPatterns')}</td>
                    <td className="py-2.5 px-3 font-sans text-slate-500">{t('modals.esg.antiPatternsStandard')}</td>
                    <td className="py-2.5 px-3 text-right font-bold text-slate-900">{t('modals.esg.violationsDetected', { count: String(violations) })}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Annual Cloud & ESG ROI Projections */}
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-900 mb-2">
              {t('modals.esg.esgRoi')}
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
                  <Leaf size={14} className="text-olive-700" />
                  {t('modals.esg.co2Offset')}
                </div>
                <div className="text-lg font-bold text-slate-900 font-mono">
                  {annualKgCo2Saved.toFixed(1)} kgCO₂e
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">{t('modals.esg.modeledCo2')}</div>
              </div>

              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
                  <Zap size={14} className="text-olive-700" />
                  {t('modals.esg.electricityReduction')}
                </div>
                <div className="text-lg font-bold text-slate-900 font-mono">
                  {annualKwhSaved.toFixed(0)} kWh / yr
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">{t('modals.esg.electricityDesc')}</div>
              </div>

              <div className="p-3.5 rounded-lg border border-slate-200 bg-slate-50">
                <div className="flex items-center gap-1.5 text-xs text-slate-500 mb-1">
                  <DollarSign size={14} className="text-emerald-700" />
                  {t('modals.esg.projectedSavings')}
                </div>
                <div className="text-lg font-bold text-emerald-800 font-mono">
                  ~${annualDollarSaved.toLocaleString()} / yr
                </div>
                <div className="text-[10px] text-slate-500 mt-0.5">{t('modals.esg.modeledGridRate')}</div>
              </div>
            </div>
          </div>

          {/* Projection methodology disclosure */}
          <p className="text-[10px] leading-relaxed text-slate-500">
            <strong className="text-slate-600">{t('modals.esg.aboutProjections')}</strong>
          </p>

          {/* Verification Sign-off Footer */}
          <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs text-slate-500">
            <div className="flex items-center gap-2">
              <Award size={16} className="text-olive-700" />
              <span>{t('modals.esg.verifiedWith')}</span>
            </div>
            <div className="font-mono text-[11px] text-slate-400">
              {t('modals.esg.methodology')}
            </div>
          </div>
        </div>
      </Modal>
    );
}
