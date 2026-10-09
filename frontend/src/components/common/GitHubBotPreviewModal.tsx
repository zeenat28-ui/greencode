import { useState } from 'react';
import { 
  GitPullRequest, CheckCircle2, AlertTriangle, ShieldCheck, 
  ArrowRight, Sparkles, X, Terminal, Bot, GitCommit, Play, Copy, Check 
} from 'lucide-react';

interface GitHubBotPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  repoName?: string;
}

export default function GitHubBotPreviewModal({
  isOpen,
  onClose,
  repoName = 'zeenat28-ui/greencode',
}: GitHubBotPreviewModalProps) {
  const [isPatched, setIsPatched] = useState(false);
  const [isPatching, setIsPatching] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!isOpen) return null;

  const handleApplyBotPatch = () => {
    setIsPatching(true);
    setTimeout(() => {
      setIsPatching(false);
      setIsPatched(true);
    }, 1200);
  };

  const handleReset = () => {
    setIsPatched(false);
  };

  const sampleDiff = isPatched ? (
`@@ -48,8 +48,8 @@ def match_warehouse_stock(order_items, warehouse_records):
-    matches = []
-    for item in order_items:
-        for stock in warehouse_records:
-            if stock.sku == item.sku:
-                matches.append(stock)
+    # Optimized with O(1) hash map lookup (GreenCode Bedrock AI)
+    stock_lookup = {stock.sku: stock for stock in warehouse_records}
+    matches = [stock_lookup[item.sku] for item in order_items if item.sku in stock_lookup]`
  ) : (
`@@ -48,8 +48,8 @@ def match_warehouse_stock(order_items, warehouse_records):
-    for item in order_items:
-        for stock in warehouse_records:  # <-- WARNING: O(N^2) quadratic nested loop
-            if stock.sku == item.sku:`
  );

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-olive-700 flex items-center justify-center text-white shadow-sm">
              <Bot size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                GreenCode Autonomous GitHub Bot
                <span className="text-[10px] px-2 py-0.5 rounded bg-blue-500/20 text-blue-300 border border-blue-400/30 font-mono">
                  Dependabot for Energy
                </span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-400/40 font-bold">
                  Interactive Simulation
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Zero-friction developer adoption: blocks carbon regressions and auto-suggests PR patches
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
          {/* Simulated GitHub PR Header */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm space-y-3">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div>
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1 text-xs font-bold px-2.5 py-1 rounded-full text-white ${
                    isPatched ? 'bg-purple-600' : 'bg-emerald-600'
                  }`}>
                    <GitPullRequest size={12} />
                    {isPatched ? 'Merged' : 'Open'}
                  </span>
                  <span className="text-sm font-bold text-slate-900">
                    feat(checkout): update warehouse stock matching logic
                  </span>
                  <span className="text-xs text-slate-400 font-mono">#142</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">
                  <span className="font-semibold text-slate-700">developer-alex</span> wants to merge 1 commit into <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-slate-800">main</code> from <code className="bg-slate-100 px-1 py-0.5 rounded font-mono text-slate-800">feature/order-sync</code>
                </p>
              </div>

              {isPatched ? (
                <button
                  onClick={handleReset}
                  className="btn-secondary text-xs px-2.5 py-1"
                >
                  Reset Simulation
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
                    <span><strong>GreenCode Quality Gate: PASSED (SCI: 94/100)</strong> — Zero energy regressions</span>
                  ) : (
                    <span><strong>GreenCode Quality Gate: FAILED (SCI: 64/100)</strong> — Quality threshold &ge; 75/100 required</span>
                  )}
                </div>
              </div>
              <span className="font-mono text-[11px] font-semibold">
                {isPatched ? '3 checks passed' : '1 check failing'}
              </span>
            </div>
          </div>

          {/* GitHub Bot Comment Container */}
          <div className="border border-slate-200 rounded-xl bg-white shadow-sm overflow-hidden">
            {/* Comment Header */}
            <div className="bg-slate-100/80 px-4 py-2.5 border-b border-slate-200 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-5 h-5 rounded-full bg-olive-800 text-white flex items-center justify-center text-[10px] font-bold">
                  GC
                </div>
                <span className="text-xs font-bold text-slate-900">greencode-bot</span>
                <span className="text-[10px] px-1.5 py-0.2 rounded bg-slate-200 text-slate-700 font-medium">bot</span>
                <span className="text-xs text-slate-400">&middot; just now</span>
              </div>
              <span className="text-[11px] text-slate-500 font-mono">Amazon Bedrock (sample output)</span>
            </div>

            {/* Comment Body */}
            <div className="p-4 space-y-3.5 text-xs text-slate-700">
              {isPatched ? (
                <div className="p-3 bg-emerald-50 rounded-lg border border-emerald-200 text-emerald-900 space-y-1">
                  <div className="font-bold flex items-center gap-1.5">
                    <CheckCircle2 size={14} className="text-emerald-600" />
                    Simulation: Patch Applied to Branch
                  </div>
                  <p className="text-[11px] text-emerald-800">
                    Simulated commit <code className="bg-emerald-100/60 px-1 rounded font-mono">ec0-89a1f2</code> (no repository was modified &mdash; real PRs are opened via <code className="font-mono">/github/pull-request</code>). Algorithmic complexity reduced from O(N²) to O(1). Estimated savings: <strong>+$410 / month</strong> in AWS EC2 compute cost.
                  </p>
                </div>
              ) : (
                <>
                  <div className="p-3 bg-rose-50/70 rounded-lg border border-rose-200 text-rose-950 space-y-1">
                    <div className="font-bold flex items-center gap-1.5">
                      <AlertTriangle size={14} className="text-rose-700" />
                      Algorithmic Energy Leak Detected in Pull Request
                    </div>
                    <p className="text-[11px] text-slate-600 leading-relaxed">
                      This pull request introduces a quadratic <code>O(N²)</code> nested loop in <code className="font-mono text-slate-800">checkout/inventory.py:48</code>. Under production basket loads, this increases CPU core utilization by 42% and adds <strong>~$380 / month</strong> in AWS EC2 compute overhead.
                    </p>
                  </div>

                  <div>
                    <div className="font-bold text-slate-900 mb-1.5 flex items-center justify-between">
                      <span>Suggested Eco-Optimization Diff</span>
                      <span className="text-[10px] font-mono text-emerald-700 font-bold">Amazon Bedrock (Claude 3.5 Sonnet)</span>
                    </div>
                    <pre className="p-3 rounded-lg bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto leading-relaxed">
                      <code>{sampleDiff}</code>
                    </pre>
                  </div>

                  <div className="pt-2 flex flex-col sm:flex-row items-center justify-between gap-3 border-t border-slate-100">
                    <div className="text-[11px] text-slate-500">
                      ⚡ Hardware RAPL verified: <strong>58% Joules reduction</strong> with 0 logic regression.
                    </div>
                    <button
                      onClick={handleApplyBotPatch}
                      disabled={isPatching}
                      className="btn-primary text-xs px-3.5 py-1.5 bg-emerald-700 hover:bg-emerald-800 flex items-center gap-1.5 w-full sm:w-auto justify-center"
                    >
                      <Sparkles size={12} />
                      {isPatching ? 'Simulating Patch...' : 'Simulate 1-Click Patch'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Why This Matters for World Tech */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2 text-xs">
            <h4 className="font-bold text-slate-900 uppercase tracking-wider text-[11px]">
              Why Every Developer Will Use This:
            </h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-[11px] text-slate-600">
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <strong>Zero Context Switching:</strong> Developers never have to leave GitHub. The bot comments and opens patches directly in their PRs.
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <strong>Automatic Gatekeeping:</strong> Prevents junior or rushed commits from introducing expensive CPU bottlenecks into production.
              </div>
              <div className="p-2.5 rounded-lg bg-slate-50 border border-slate-100">
                <strong>Instant ROI:</strong> Every merged patch immediately reduces the monthly cloud hosting bill.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

