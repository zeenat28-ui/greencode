import { CheckCircle2, XCircle, Copy } from 'lucide-react';
import { useT } from '../../i18n/I18nContext';

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
  const t = useT();
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  return (
    <div className="space-y-4 max-w-full overflow-hidden">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 max-w-full">
      {/* Original Code */}
         <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-rose-200/90 dark:border-rose-800/50 bg-white dark:bg-zinc-900">
           <div className="flex items-center justify-between px-3 py-2 bg-rose-50/80 dark:bg-rose-900/20 border-b border-rose-200/80 dark:border-rose-800/50">
             <div className="flex items-center gap-1.5">
               <XCircle className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
               <span className="font-mono font-semibold text-rose-900 dark:text-rose-300 text-xs">{t('codeDiff.before')}</span>
             </div>
             <button
               onClick={() => handleCopy(originalCode)}
               className="text-zinc-400 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300 p-1 rounded"
               title={t('codeDiff.copyOriginal')}
             >
              <Copy size={13} />
            </button>
          </div>
          <pre className="text-xs font-mono text-zinc-800 dark:text-zinc-200 p-3.5 bg-rose-50/20 dark:bg-rose-900/10 overflow-x-auto m-0 leading-relaxed">
            <code>{originalCode}</code>
          </pre>
        </div>

        {/* Refactored Code */}
        <div className="min-w-0 max-w-full overflow-hidden rounded-lg border border-emerald-200/90 dark:border-emerald-800/50 bg-white dark:bg-zinc-900">
          <div className="flex items-center justify-between px-3 py-2 bg-emerald-50/80 dark:bg-emerald-900/20 border-b border-emerald-200/80 dark:border-emerald-800/50">
            <div className="flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              <span className="font-mono font-semibold text-emerald-950 dark:text-emerald-300 text-xs">{t('codeDiff.after')}</span>
            </div>
            <button
              onClick={() => handleCopy(refactoredCode)}
              className="text-zinc-400 hover:text-zinc-700 dark:text-zinc-500 dark:hover:text-zinc-300 p-1 rounded"
              title={t('codeDiff.copyOptimized')}
            >
              <Copy size={13} />
            </button>
          </div>
          <pre className="text-xs font-mono text-zinc-900 dark:text-zinc-100 p-3.5 bg-emerald-50/20 dark:bg-emerald-900/10 overflow-x-auto m-0 leading-relaxed">
            <code>{refactoredCode}</code>
          </pre>
        </div>
      </div>

      {showActions && onApply && (
        <div className="flex justify-end pt-3 border-t border-zinc-200 dark:border-zinc-700 gap-2.5">
          <button
            onClick={() => handleCopy(refactoredCode)}
            className="btn-secondary text-xs flex items-center gap-1.5"
          >
            {t('codeDiff.copyPatch')}
          </button>
          <button
            onClick={onApply}
            disabled={isApplying}
            className="btn-primary text-xs flex items-center gap-1.5"
          >
            {isApplying ? t('codeDiff.applyingPatch') : t('codeDiff.applyPatch')}
          </button>
        </div>
      )}
    </div>
  );
}
