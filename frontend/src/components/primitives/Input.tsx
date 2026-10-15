import { InputHTMLAttributes, forwardRef, useId } from 'react';
import { cn } from '../../lib/utils';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, helperText, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id || `input-${generatedId}`;
    const hasError = !!error;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="label mb-1"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={cn(
            'w-full px-3 py-1.5 bg-[var(--gc-bg-default)] border rounded-md text-sm text-[var(--gc-text-primary)]',
            'placeholder:text-[var(--gc-text-tertiary)]',
            hasError
              ? 'border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/25'
              : 'border-[var(--gc-border-default)] focus:outline-none focus:ring-2 focus:ring-emerald-600/25 focus:border-emerald-600',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1 text-[11px] text-rose-600 font-medium">{error}</p>
        )}
        {helperText && !error && (
          <p className="mt-1 text-[11px] text-zinc-500">{helperText}</p>
        )}
      </div>
    );
  }
);
Input.displayName = 'Input';

export { Input };
