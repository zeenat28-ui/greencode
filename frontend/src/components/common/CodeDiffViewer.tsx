import { CheckCircle2, XCircle, Copy } from 'lucide-react';

interface CodeDiffViewerProps {
  originalCode: string;
  refactoredCode: string;
  language?: string;
  onApply?: () => void;
  showActions?: boolean;
  isApplying?: boolean;
}

export default function CodeDiffViewer({
  originalCode,
  refactoredCode,
  onApply,
  showActions = true,
  isApplying = false,
}: CodeDiffViewerProps) {
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-4 max-w-full overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-full">
        {/* Original Code */}
        <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-rose-200/90 bg-white">
          <div className="flex items-center justify-between px-3 py-2 bg-rose-50/80 border-b border-rose-200/80">
            <div className="flex items-center gap-1.5">
              <XCircle className="w-3.5 h-3.5 text-rose-600" />
              <span className="font-mono font-semibold text-rose-900 text-xs">Before (Baseline AST)</span>
            </div>
            <button
              onClick={() => handleCopy(originalCode)}
              className="text-zinc-400 hover:text-zinc-700 p-1 rounded"
              title="Copy original snippet"
            >
              <Copy size={13} />
            </button>
          </div>
          <pre className="text-xs font-mono text-zinc-800 p-3.5 bg-rose-50/20 overflow-x-auto m-0 leading-relaxed">
            <code>{originalCode}</code>
          </pre>
        </div>

        {/* Refactored Code */}
        <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-emerald-200/90 bg-white">
          <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/80 border-b border-emerald-200/80">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
              <span className="font-mono font-semibold text-emerald-950 text-xs">After (Synthesized Patch)</span>
            </div>
            <button
              onClick={() => handleCopy(refactoredCode)}
              className="text-zinc-400 hover:text-zinc-700 p-1 rounded"
              title="Copy optimized patch"
            >
              <Copy size={13} />
            </button>
          </div>
          <pre className="text-xs font-mono text-zinc-900 p-3.5 bg-emerald-50/20 overflow-x-auto m-0 leading-relaxed">
            <code>{refactoredCode}</code>
          </pre>
        </div>
      </div>

      {showActions && onApply && (
        <div className="flex justify-end pt-3 border-t border-zinc-200 gap-2.5">
          <button
            onClick={() => handleCopy(refactoredCode)}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            Copy Patch
          </button>
          <button
            onClick={onApply}
            disabled={isApplying}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            {isApplying ? 'Applying Patch...' : 'Apply Patch'}
          </button>
        </div>
      )}
    </div>
  );
}
