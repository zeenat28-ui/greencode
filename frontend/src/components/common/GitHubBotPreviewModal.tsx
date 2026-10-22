import { useState } from 'react';
import { 
  GitPullRequest, CheckCircle2, AlertTriangle, 
  Sparkles, X, Bot, Copy, Check 
} from 'lucide-react';
import { Modal } from '../primitives/Modal';
import { useT } from '../../i18n/I18nContext';
import { authHeaders } from '../../services/api';

interface GitHubBotPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  repoName?: string;
}

const DEFAULT_PR_SNIPPET = `def match_warehouse_stock(order_items, warehouse_records):
    matches = []
    for item in order_items:
        for stock in warehouse_records:
            if stock.sku == item.sku:
                matches.append(stock)
    return matches`;

export default function GitHubBotPreviewModal({
  isOpen,
  onClose,
  repoName,
}: GitHubBotPreviewModalProps) {
  const t = useT();
  const [isPatched, setIsPatched] = useState(false);
  const [isPatching, setIsPatching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [liveDiff, setLiveDiff] = useState<string>('');
  const [liveSuggestionMd, setLiveSuggestionMd] = useState<string>('');
  const [refactorMeta, setRefactorMeta] = useState<{
    model: string;
    source: string;
    behaviourVerified: boolean;
    energyReductionPct: number;
    gateVerdict: string;
  } | null>(null);
  const [copiedField, setCopiedField] = useState<string | null>(null);

  const handleApplyBotPatch = async () => {
    setIsPatching(true);
    setError(null);
    try {
      const refactorRes = await fetch('/api/refactor', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          source_code: DEFAULT_PR_SNIPPET,
          language: 'python',
          violation_type: 'nested_loop_lookup',
          file_path: 'checkout/inventory.py',
          start_line: 48,
          end_line: 55,
        }),
      });

      if (!refactorRes.ok) {
        setError(`Refactor service returned HTTP ${refactorRes.status}. No patch was applied.`);
        return;
      }

      const data = await refactorRes.json();
      const energyReductionPct = Number(data.estimated_energy_reduction_pct ?? 0);

      // Evaluate the PR against the team's carbon budget. The API models the
      // gate as *additional* projected kg CO2e (it must be >= 0), so a net
      // reduction contributes 0 to consumption. The signed delta is kept
      // locally for display.
      const carbonDeltaGco2e = Number((-energyReductionPct * 0.25).toFixed(2));
      const gateRes = await fetch('/api/energy/budgets/evaluate-pr', {
        method: 'POST',
        headers: authHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({
          // The organisation comes from the verified access token.
          team_id: 'core-infra',
          additional_projected_kg_co2e: Math.max(0, carbonDeltaGco2e),
        }),
      });
      const gateData = gateRes.ok ? await gateRes.json() : null;

      setLiveDiff(
        data.unified_diff ||
          `--- a/checkout/inventory.py\n+++ b/checkout/inventory.py\n@@ -48,7 +48,4 @@\n-${DEFAULT_PR_SNIPPET.split('\n').join('\n-')}\n+${(data.refactored_code || '').split('\n').join('\n+')}`
      );
      setLiveSuggestionMd(data.github_suggestion_markdown || '');
      setRefactorMeta({
        model: data.model || 'Deterministic AST Engine',
        source: data.source || 'ast_verifier',
        behaviourVerified: Boolean(data.behaviour_verified),
        energyReductionPct,
        gateVerdict: gateData?.verdict || 'PENDING',
      });
      setIsPatched(true);
    } catch (err: any) {
      // Honest failure: do NOT claim a patch was verified when the call errored.
      setError(err?.message || 'Refactor request failed. No patch was applied.');
    } finally {
      setIsPatching(false);
    }
  };

  const handleReset = () => {
    setIsPatched(false);
    setLiveDiff('');
    setLiveSuggestionMd('');
    setRefactorMeta(null);
    setError(null);
  };

  const copyText = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(label);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const displayedDiff =
    isPatched && liveDiff
      ? liveDiff
      : `@@ -48,8 +48,8 @@ def match_warehouse_stock(order_items, warehouse_records):
-    matches = []
-    for item in order_items:
-        for stock in warehouse_records:  # <-- WARNING: O(N^2) quadratic nested loop
-            if stock.sku == item.sku:
-                matches.append(stock}`;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      showCloseButton={false}
      size="lg"
      overlayClassName="items-center bg-slate-900/60"
      className="!max-w-3xl border-slate-200 overflow-hidden"
      contentClassName="p-0 overflow-visible"
    >
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-olive-700 flex items-center justify-center text-white shadow-sm">
              <Bot size={18} />
            </div>
            <div>
               <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                 {t('modals.githubBot.title')}
                 <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30 font-mono">
                   {t('modals.githubBot.subtitle')}
                 </span>
                 <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/40 font-bold">
                   {t('modals.githubBot.engineBadge')}
                 </span>
               </h3>
               <p className="text-[11px] text-slate-400">
                 {t('modals.githubBot.tagline')}
               </p>
             </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-5 text-slate-800 max-h-[82vh] overflow-y-auto bg-slate-50/50">
          {/* GitHub PR Header */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
               <div className="flex items-center gap-2">
                   <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full text-white ${
                     isPatched ? 'bg-purple-600' : 'bg-emerald-600'
                   }`}>
                     <GitPullRequest size={12} />
                     {isPatched ? t('modals.githubBot.patchVerified') : t('modals.githubBot.previewPr')}
                   </span>
                   <span className="text-sm font-bold text-slate-900">
                     {t('modals.githubBot.prTitle')}
                   </span>
                   <span className="text-xs text-slate-400 font-mono">{repoName ? t('modals.githubBot.exampleRepo', { repo: repoName }) : t('modals.githubBot.examplePr')}</span>
                 </div>
                 <p className="text-xs text-slate-500 mt-1">
                   {t('modals.githubBot.targetBranchLabel', { branch: t('modals.githubBot.targetBranch') })} <code className="bg-slate-100 dark:bg-zinc-800 px-1 py-0.5 rounded font-mono text-slate-800 dark:text-zinc-200">{t('modals.githubBot.sourceBranch')}</code>
                 </p>
              </div>

               {isPatched ? (
                 <button
                   onClick={handleReset}
                   className="btn-secondary text-xs px-2.5 py-1"
                 >
                   {t('modals.githubBot.resetDiff')}
                 </button>
               ) : null}
            </div>

            {/* CI Status Checks Widget */}
             <div className={`p-3 rounded-lg border text-xs flex items-center justify-between ${
               isPatched 
                 ? 'bg-emerald-50 border-emerald-200 text-emerald-900' 
                 : 'bg-rose-50 border-rose-200 text-rose-900'
             }`}>
               <div className="flex items-center gap-2">
                 {isPatched ? (
                   <CheckCircle2 size={16} className="text-emerald-600 shrink-0" />
                 ) : (
                   <AlertTriangle size={16} className="text-rose-600 shrink-0" />
                 )}
                 <div className="font-medium">
                   {isPatched ? (
                     <span>
                       <strong>{t('modals.githubBot.qualityGate', { status: refactorMeta?.gateVerdict || 'PASSED' })}</strong> — {t('modals.githubBot.behaviourVerified', { status: refactorMeta?.behaviourVerified ? t('modals.githubBot.behaviourVerifiedPassed') : t('modals.githubBot.behaviourVerifiedDefault') })}
                     </span>
                   ) : (
                     <span><strong>{t('modals.githubBot.qualityGate', { status: 'PENDING' })}</strong> — {t('modals.githubBot.applyPatchHint')}</span>
                   )}
                 </div>
               </div>
               <span className="font-mono text-[11px] font-semibold">
                 {isPatched ? t('modals.githubBot.checksRunning') : t('modals.githubBot.notYetRun')}
               </span>
             </div>

            {error && (
              <div className="p-3 rounded-lg border bg-rose-50 border-rose-200 text-rose-900 text-xs flex items-start gap-2">
                <AlertTriangle size={15} className="text-rose-600 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}
          </div>

          {/* GitHub Bot Comment Container */}
          <div className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
            {/* Comment Header */}
            <div className="bg-slate-100/80 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-olive-800 text-white flex items-center justify-center text-[10px] font-bold">
                  GC
                </div>
                 <span className="text-xs font-bold text-slate-900 dark:text-zinc-200">{t('modals.githubBot.botName')}</span>
                 <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-medium">{t('modals.githubBot.botTag')}</span>
                 <span className="text-xs text-slate-400 dark:text-zinc-400">&middot; {t('modals.githubBot.apiRef')}</span>
               </div>
               <span className="text-[11px] text-slate-500 dark:text-zinc-400 font-mono">
                 {refactorMeta ? `${refactorMeta.model} (${refactorMeta.source})` : t('modals.githubBot.apiRefPost')}
              </span>
            </div>

            {/* Comment Body */}
            <div className="p-4 space-y-3.5 text-xs text-slate-700">
              {isPatched ? (
                <div className="space-y-3">
                  <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-900 space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <CheckCircle2 size={14} className="text-emerald-600" />
                      {t('modals.githubBot.diffSynthesized', { pct: String(refactorMeta?.energyReductionPct ?? 0) })}
                    </div>
                    <p className="text-[11px] text-emerald-800">
                      {t('modals.githubBot.generatedBy', { model: refactorMeta?.model || 'Deterministic AST Engine' })}
                    </p>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-bold text-slate-900">{t('modals.githubBot.diffLabel')}</span>
                    <div className="flex items-center gap-2">
                      <button
                        type="button"
                        onClick={() => copyText(displayedDiff, 'diff')}
                        className="px-2.5 py-1 rounded border border-slate-200 bg-slate-50 hover:bg-slate-100 text-[11px] font-medium flex items-center gap-1"
                      >
                        {copiedField === 'diff' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                        {copiedField === 'diff' ? t('modals.githubBot.copiedDiff') : t('modals.githubBot.copyDiff')}
                      </button>
                      {liveSuggestionMd && (
                        <button
                          type="button"
                          onClick={() => copyText(liveSuggestionMd, 'suggestion')}
                          className="px-2.5 py-1 rounded border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 text-[11px] font-medium flex items-center gap-1"
                        >
                           {copiedField === 'suggestion' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                           {copiedField === 'suggestion' ? t('modals.githubBot.copiedSuggestion') : t('modals.githubBot.copySuggestion')}
                        </button>
                      )}
                    </div>
                  </div>
                  <pre className="p-3 rounded-lg bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed">
                    <code>{displayedDiff}</code>
                  </pre>
                </div>
              ) : (
                <>
                  <div className="p-3 bg-rose-50/70 rounded-lg border border-rose-200 text-rose-950 space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <AlertTriangle size={14} className="text-rose-700" />
                      {t('modals.githubBot.leakTitle')}
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: t('modals.githubBot.leakDesc', { file: 'checkout/inventory.py', line: '48' }) }}
                    />
                  </div>

                  <div>
                    <div className="font-bold text-slate-900 mb-1.5 flex items-center justify-between">
                       <span>{t('modals.githubBot.unoptimizedHunk')}</span>
                       <span className="text-[10px] font-mono text-rose-700 font-bold">{t('modals.githubBot.violation', { type: 'nested_loop_lookup' })}</span>
                    </div>
                    <pre className="p-3 rounded-lg bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed">
                      <code>{displayedDiff}</code>
                    </pre>
                  </div>

                  <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100">
                     <div className="text-[11px] text-slate-500">
                       {t('modals.githubBot.executionNote')}
                     </div>
                     <button
                       onClick={handleApplyBotPatch}
                       disabled={isPatching}
                       className="btn-primary text-xs px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 flex items-center gap-1.5 w-full sm:w-auto justify-center"
                     >
                       <Sparkles size={12} />
                       {isPatching ? t('modals.githubBot.synthesizing') : t('modals.githubBot.generatePatch')}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Why This Matters for World Tech */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white dark:bg-zinc-800/50 space-y-2 text-xs">
            <h4 className="font-bold text-slate-900 dark:text-zinc-100 uppercase tracking-wider text-[11px]">
              {t('modals.githubBot.whyThisMatters')}
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px] text-slate-600 dark:text-zinc-300">
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-zinc-800/30 border border-slate-100 dark:border-zinc-700">
                <strong>{t('modals.githubBot.valueProps.zeroContextSwitching')}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-zinc-800/30 border border-slate-100 dark:border-zinc-700">
                <strong>{t('modals.githubBot.valueProps.automaticGatekeeping')}</strong>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-zinc-800/30 border border-slate-100 dark:border-zinc-700">
                <strong>{t('modals.githubBot.valueProps.instantRoi')}</strong>
              </div>
            </div>
          </div>
        </div>
      </Modal>
  );
}

