import { forwardRef } from 'react';
import { cn } from '../../lib/utils';
import { AlertCircle, RefreshCw } from 'lucide-react';

export interface ErrorStateProps extends React.HTMLAttributes<HTMLDivElement> {
  error?: string | Error;
  onRetry?: () => void;
  title?: string;
  description?: string;
}

export const ErrorState = forwardRef<HTMLDivElement, ErrorStateProps>(
  ({ className, error, onRetry, title = 'Something went wrong', description, ...props }, ref) => {
    const message = error instanceof Error ? error.message : error || description;

    return (
      <div
        ref={ref}
        className={cn(
          'flex flex-col items-center justify-center text-center py-10 px-6',
          className
        )}
        {...props}
      >
        <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 mb-4">
          <AlertCircle size={22} />
        </div>
        <h3 className="text-base font-semibold text-zinc-900 mb-1">{title}</h3>
        {message && <p className="text-xs text-zinc-500 mb-4 max-w-md leading-relaxed">{message}</p>}
        {onRetry && (
          <button
            onClick={onRetry}
            type="button"
            className="btn-secondary text-xs px-3 py-1.5 flex items-center gap-1.5"
          >
            <RefreshCw size={12} />
            Try again
          </button>
        )}
      </div>
    );
  }
);
ErrorState.displayName = 'ErrorState';
