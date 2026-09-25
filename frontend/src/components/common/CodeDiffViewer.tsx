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
  language = 'python',
  onApply,
  showActions = true,
  isApplying = false,
}: CodeDiffViewerProps) {
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Original Code */}
        <div>
          <div className="flex items-center justify-between mb-2 px-3 py-2 bg-red-50 border-b border-red-200 rounded-t-lg">
            <div className="flex items-center gap-2">
              <XCircle className="w-4 h-4 text-red-600" />
              <span className="font-semibold text-red-800 text-sm">Original Code</span>
            </div>
            <button
              onClick={() => handleCopy(originalCode)}
              className="text-slate-400 hover:text-slate-600"
              title="Copy"
            >
              <Copy size={14} />
            </button>
          </div>
          <div className="border border-slate-200 rounded-b-lg overflow-hidden">
            <pre className="text-xs font-mono text-slate-700 p-4 bg-slate-50 overflow-x-auto m-0">
              <code>{originalCode}</code>
            </pre>
          </div>
        </div>

        {/* Refactored Code */}
        <div>
          <div className="flex items-center justify-between mb-2 px-3 py-2 bg-green-50 border-b border-green-200 rounded-t-lg">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-green-600" />
              <span className="font-semibold text-green-800 text-sm">Eco-Refactored Code</span>
            </div>
            <button
              onClick={() => handleCopy(refactoredCode)}
              className="text-slate-400 hover:text-slate-600"
              title="Copy"
            >
              <Copy size={14} />
            </button>
          </div>
          <div className="border border-slate-200 rounded-b-lg overflow-hidden">
            <pre className="text-xs font-mono text-slate-700 p-4 bg-slate-50 overflow-x-auto m-0">
              <code>{refactoredCode}</code>
            </pre>
          </div>
        </div>
      </div>

      {showActions && onApply && (
        <div className="flex justify-end pt-4 border-t border-slate-200 gap-3">
          <button
            onClick={() => handleCopy(refactoredCode)}
            className="btn-secondary flex items-center gap-2"
          >
            Copy Fix
          </button>
          <button
            onClick={onApply}
            disabled={isApplying}
            className="btn-primary flex items-center gap-2"
          >
            {isApplying ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Applying Fix...
              </>
            ) : (
              'Apply This Fix'
            )}
          </button>
        </div>
      )}
    </div>
  );
}
