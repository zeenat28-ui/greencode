import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export type LoadingStateVariant = 'spinner' | 'skeleton';

export interface LoadingStateProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: LoadingStateVariant;
  lines?: number;
  text?: string;
}

export const LoadingState = forwardRef<HTMLDivElement, LoadingStateProps>(
  ({ className, variant = 'spinner', lines = 3, text, ...props }, ref) => {
    if (variant === 'skeleton') {
      return (
        <div
          ref={ref}
          className={cn('animate-pulse space-y-3', className)}
          {...props}
        >
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className="h-4 bg-zinc-200 rounded"
              style={{ width: `${100 - (i % 3) * 10}%` }}
            />
          ))}
        </div>
      );
    }

    return (
      <div
        ref={ref}
        className={cn('flex flex-col items-center justify-center py-10 text-zinc-500', className)}
        {...props}
      >
        <div className="w-10 h-10 border-3 border-emerald-600 border-t-transparent rounded-full animate-spin mb-3" />
        {text && <p className="text-xs">{text}</p>}
      </div>
    );
  }
);
LoadingState.displayName = 'LoadingState';
