import { TextareaHTMLAttributes, forwardRef, useId } from 'react';
import { cn } from '../../lib/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, label, error, helperText, id, ...props }, ref) => {
    const generatedId = useId();
    const textareaId = id || `textarea-${generatedId}`;
    const hasError = !!error;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={textareaId}
            className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-500 mb-1"
          >
            {label}
          </label>
        )}
        <textarea
          id={textareaId}
          ref={ref}
          className={cn(
            'w-full px-3.5 py-2 bg-white border rounded-lg text-sm text-zinc-900',
            'placeholder-zinc-400 transition-all duration-150 shadow-xs resize-y min-h-[100px]',
            hasError
              ? 'border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/25'
              : 'border-zinc-200 focus:outline-none focus:ring-2 focus:ring-emerald-600/25 focus:border-emerald-600',
            className
          )}
          {...props}
        />
        {error && <p className="mt-1 text-[11px] text-rose-600 font-medium">{error}</p>}
        {helperText && !error && <p className="mt-1 text-[11px] text-zinc-500">{helperText}</p>}
      </div>
    );
  }
);
Textarea.displayName = 'Textarea';
