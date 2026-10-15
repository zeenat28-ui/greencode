import React, { useState, useEffect } from 'react';
import { ShieldAlert, Sliders, Save, CheckCircle2, FileCode, Terminal, Play, AlertTriangle } from 'lucide-react';
import { useT } from '../i18n/I18nContext';

const SAMPLE_TF = `resource "aws_instance" "api_node" {
  ami           = "ami-0c55b159cbfafe1f0"
  instance_type = "c5.2xlarge"
}

resource "aws_ebs_volume" "app_storage" {
  type = "gp2"
  size = 250
}`;

const SAMPLE_K8S = `apiVersion: apps/v1
kind: Deployment
metadata:
  name: billing-worker
spec:
  template:
    spec:
      containers:
        - name: worker
          image: greencode/worker:latest`;

const SAMPLE_DOCKER = `FROM python:3.11
RUN apt-get update && apt-get install -y build-essential`;

export default function Policies() {
  const t = useT();
  const [maxRegression, setMaxRegression] = useState(25.0);
  const [minGreenScore, setMinGreenScore] = useState(80.0);
  const [autoBlock, setAutoBlock] = useState(true);
  const [autoRollback, setAutoRollback] = useState(true);
  const [dirtyGridLimit, setDirtyGridLimit] = useState(450.0);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const [customRules, setCustomRules] = useState<any[]>([]);
  const [customTestCode, setCustomTestCode] = useState(
    'import time\ndef wait_loop(tasks):\n    for t in tasks:\n        time.sleep(0.2)\n'
  );
  const [customEvalResult, setCustomEvalResult] = useState<any>(null);
  const [evaluatingCustom, setEvaluatingCustom] = useState(false);

  const [iacContent, setIacContent] = useState(SAMPLE_TF);
  const [iacFilePath, setIacFilePath] = useState('infra/main.tf');
  const [iacResult, setIacResult] = useState<any>(null);
  const [auditingIac, setAuditingIac] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('greencode_token');
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
    fetch('/api/policies/1', { headers })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        const p = data?.policy || data;
        if (p && typeof p === 'object') {
          if (p.max_regression_pct !== undefined) setMaxRegression(Number(p.max_regression_pct));
          if (p.max_sci_score !== undefined) setMinGreenScore(Number(p.max_sci_score));
          if (p.auto_block_deploy !== undefined) setAutoBlock(Boolean(p.auto_block_deploy));
          if (p.auto_rollback_k8s !== undefined) setAutoRollback(Boolean(p.auto_rollback_k8s));
          if (p.dirty_grid_threshold_gco2e !== undefined) setDirtyGridLimit(Number(p.dirty_grid_threshold_gco2e));
        }
      })
      .catch(() => {});

    fetch('/api/policies/custom-rules')
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && Array.isArray(data.rules)) {
          setCustomRules(data.rules);
        }
      })
      .catch(() => {});
  }, []);

  const handleSave = async () => {
    setSaveError(null);
    setSavedSuccess(false);
    try {
      const token = localStorage.getItem('greencode_token');
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      };
      const res = await fetch('/api/policies', {
        method: 'POST',
        headers,
        body: JSON.stringify({
          org_id: 1,
          name: t('policies.policyName'),
          max_regression_pct: maxRegression,
          max_sci_score: minGreenScore,
          auto_block_deploy: autoBlock,
          auto_rollback_k8s: autoRollback,
          dirty_grid_threshold_gco2e: dirtyGridLimit,
        }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({} as any));
        setSaveError(body?.detail || `Save failed (HTTP ${res.status}).`);
        return;
      }
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 3000);
    } catch (err: any) {
      setSaveError(err?.message || 'Could not reach the policy service.');
    }
  };

  const handleEvaluateCustomRules = async () => {
    setEvaluatingCustom(true);
    try {
      const res = await fetch('/api/policies/custom-rules/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          source_code: customTestCode,
          language: 'python',
          file_path: 'worker_poll.py',
        }),
      });
      if (res.ok) {
        setCustomEvalResult(await res.json());
      }
    } catch {
      // Non-blocking
    } finally {
      setEvaluatingCustom(false);
    }
  };

  const handleRunIacAudit = async (overrideContent?: string, overridePath?: string) => {
    setAuditingIac(true);
    const targetContent = overrideContent ?? iacContent;
    const targetPath = overridePath ?? iacFilePath;
    try {
      const res = await fetch('/api/kubernetes/iac-audit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: targetContent,
          file_path: targetPath,
        }),
      });
      if (res.ok) {
        setIacResult(await res.json());
      }
    } catch {
      // Non-blocking
    } finally {
      setAuditingIac(false);
    }
  };

  return (
    <div className="space-y-5">
      {/* Header */}
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 border-b border-zinc-200/80 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-semibold text-zinc-950 dark:text-zinc-100 tracking-tight">{t('policies.title')}</h1>
            <span className="badge-olive">CI/CD &amp; IaC Rules</span>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-0.5">
            {t('policies.subtitle')}
          </p>
        </div>
        <button 
          onClick={handleSave}
          className="btn-primary text-xs px-3.5 py-2 flex items-center gap-1.5"
        >
          <Save className="w-3.5 h-3.5" /> {t('policies.saveButton')}
        </button>
      </div>

      {savedSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm p-4 rounded-xl flex items-center gap-2">
            <CheckCircle2 className="w-5 h-5 text-emerald-600" />
            <span>{t('policies.savedSuccess')}</span>
        </div>
      )}

      {saveError && (
        <div className="bg-red-50 border border-red-200 text-red-800 text-sm p-4 rounded-xl flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-red-600" />
          <span>{saveError}</span>
        </div>
      )}

      {/* Rules Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm space-y-5">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100 text-base flex items-center gap-2">
            <Sliders className="w-4 h-4 text-emerald-600" /> {t('policies.cicdGating')}
          </h2>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1">
              {t('policies.maxRegression')}
            </label>
            <input 
              type="number" 
              value={maxRegression} 
              onChange={(e) => setMaxRegression(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">{t('policies.regressionHint')}</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1">
              {t('policies.minGreenScore')}
            </label>
            <input 
              type="number" 
              value={minGreenScore} 
              onChange={(e) => setMinGreenScore(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">{t('policies.greenScoreHint')}</span>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoBlock} 
                onChange={(e) => setAutoBlock(e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded"
              />
              <span className="text-sm font-medium text-slate-900 dark:text-slate-200">{t('policies.autoBlock')}</span>
            </label>
          </div>
        </div>

        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm space-y-5">
          <h2 className="font-semibold text-slate-900 dark:text-slate-100 text-base flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-blue-600" /> {t('policies.k8sSentinel')}
          </h2>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1">
              {t('policies.liveRollbackLimit')}
            </label>
            <input 
              type="number" 
              value={35.0} 
              disabled
              className="w-full bg-slate-100 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-500 outline-none"
            />
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">{t('policies.rollbackHint')}</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider block mb-1">
              {t('policies.dirtyGridLimit')}
            </label>
            <input 
              type="number" 
              value={dirtyGridLimit} 
              onChange={(e) => setDirtyGridLimit(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 dark:text-slate-400 mt-1 block">{t('policies.dirtyGridHint')}</span>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoRollback} 
                onChange={(e) => setAutoRollback(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-slate-900 dark:text-slate-200">{t('policies.autoRollback')}</span>
            </label>
          </div>
        </div>
      </div>

      {/* Declarative Custom YAML Rules (.greencode-rules.yaml) */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2">
            <div>
              <h2 className="font-semibold text-slate-900 dark:text-slate-100 text-base flex items-center gap-2">
                <FileCode className="w-4 h-4 text-emerald-600" /> {t('policies.customYaml.title')}
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                {t('policies.customYaml.description')}
              </p>
            </div>
            <button
              onClick={handleEvaluateCustomRules}
              disabled={evaluatingCustom}
              className="bg-slate-900 hover:bg-slate-800 text-white text-xs font-medium px-3.5 py-2 rounded-lg flex items-center gap-1.5 transition-colors"
            >
              <Play className="w-3.5 h-3.5" /> {evaluatingCustom ? t('policies.evaluating') : t('policies.testRules')}
            </button>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider block">
                {t('policies.customYaml.activeRules', { count: customRules.length })}
              </span>
              <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
                {customRules.map((rule) => (
                  <div key={rule.id} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
                    <div className="flex justify-between items-center">
                      <span className="font-mono font-bold text-slate-900 dark:text-slate-200">{rule.id}</span>
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 font-semibold">
                        {rule.severity} (-{rule.deduction} pts)
                      </span>
                    </div>
                    <div className="font-medium text-slate-700 dark:text-slate-300">{rule.title}</div>
                    <div className="text-slate-500 dark:text-slate-400">{rule.fix_guidance}</div>
                  </div>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              <span className="text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider block">
                {t('policies.customYaml.sandbox')}
              </span>
              <textarea
                rows={5}
                value={customTestCode}
                onChange={(e) => setCustomTestCode(e.target.value)}
                className="w-full font-mono text-xs bg-slate-900 text-emerald-300 border border-slate-800 rounded-lg p-3 outline-none"
              />
              {customEvalResult && (
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
                  <div className="flex justify-between font-semibold text-slate-900 dark:text-slate-200">
                    <span>{t('policies.customYaml.matchedFindings', { count: customEvalResult.violations_count })}</span>
                    <span>{t('policies.customYaml.greenScore', { score: customEvalResult.green_score })}</span>
                  </div>
                  {(customEvalResult.violations || []).map((v: any, idx: number) => (
                    <div key={idx} className="text-amber-700 font-mono">
                      [{v.violation_type}] {t('policies.customYaml.line', { line: v.line_number })}: {v.title}
                    </div>
                  ))}
                </div>
              )}
            </div>
        </div>
      </div>

      {/* Infrastructure-as-Code (Terraform, Kubernetes, Dockerfile) FinOps & GreenOps Linter */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
          <div>
            <h2 className="font-semibold text-slate-900 dark:text-slate-100 text-base flex items-center gap-2">
              <Terminal className="w-4 h-4 text-blue-600" /> {t('policies.iacLinter.title')}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t('policies.iacLinter.description')}
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => {
                setIacContent(SAMPLE_TF);
                setIacFilePath('infra/main.tf');
                handleRunIacAudit(SAMPLE_TF, 'infra/main.tf');
              }}
                className="text-xs px-2.5 py-1.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium"
            >
              {t('policies.iacLinter.sampleTf')}
            </button>
            <button
              onClick={() => {
                setIacContent(SAMPLE_K8S);
                setIacFilePath('k8s/deployment.yaml');
                handleRunIacAudit(SAMPLE_K8S, 'k8s/deployment.yaml');
              }}
                className="text-xs px-2.5 py-1.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium"
            >
              {t('policies.iacLinter.sampleK8s')}
            </button>
            <button
              onClick={() => {
                setIacContent(SAMPLE_DOCKER);
                setIacFilePath('Dockerfile');
                handleRunIacAudit(SAMPLE_DOCKER, 'Dockerfile');
              }}
                className="text-xs px-2.5 py-1.5 rounded bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-300 font-medium"
            >
              {t('policies.iacLinter.sampleDocker')}
            </button>
            <button
              onClick={() => handleRunIacAudit()}
              disabled={auditingIac}
              className="bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-medium px-3.5 py-1.5 rounded-lg"
            >
              {auditingIac ? t('policies.iacLinter.auditing') : t('policies.iacLinter.auditButton')}
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <textarea
            rows={7}
            value={iacContent}
            onChange={(e) => setIacContent(e.target.value)}
            className="w-full font-mono text-xs bg-slate-900 text-slate-100 border border-slate-800 rounded-lg p-3 outline-none"
          />

          <div className="space-y-2">
            {iacResult ? (
              <div className="space-y-2">
                <div className="grid grid-cols-3 gap-2">
                  <div className="p-2.5 rounded-xl bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
                    <span className="text-[11px] text-slate-500 dark:text-slate-400 block">{t('policies.iacLinter.greenScore')}</span>
                    <span className="text-sm font-bold text-slate-900 dark:text-slate-100 font-mono">{iacResult.green_score} / 100</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-800">
                    <span className="text-[11px] text-emerald-700 dark:text-emerald-300 block">{t('policies.iacLinter.monthlySavings')}</span>
                    <span className="text-sm font-bold text-emerald-800 dark:text-emerald-300 font-mono">${iacResult.estimated_monthly_usd_savings} / mo</span>
                  </div>
                  <div className="p-2.5 rounded-xl bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                    <span className="text-[11px] text-blue-700 dark:text-blue-300 block">{t('policies.iacLinter.carbonAvoided')}</span>
                    <span className="text-sm font-bold text-blue-800 dark:text-blue-300 font-mono">{iacResult.estimated_annual_co2_saved_kg} kg CO2e</span>
                  </div>
                </div>
                <div className="space-y-2 max-h-40 overflow-y-auto pr-1">
                  {(iacResult.findings || []).map((f: any, idx: number) => (
                    <div key={idx} className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs space-y-1">
                      <div className="flex justify-between font-semibold text-slate-900 dark:text-slate-200">
                        <span>{f.title}</span>
                        <span className="text-emerald-700 dark:text-emerald-300">-${f.estimated_monthly_usd_savings}/mo</span>
                      </div>
                      <div className="text-slate-600 dark:text-slate-400">{f.description}</div>
                      <pre className="bg-slate-900 text-emerald-300 p-2 rounded font-mono text-[11px] overflow-x-auto">
                        {f.recommended_patch}
                      </pre>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="h-full flex items-center justify-center p-6 rounded-lg border border-dashed border-slate-200 dark:border-slate-700 text-xs text-slate-400 dark:text-slate-500">
                {t('policies.iacLinter.placeholder')}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}


