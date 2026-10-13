import { SelectHTMLAttributes, forwardRef, useId } from 'react';
import { cn } from '../../lib/utils';
import { ChevronDown } from 'lucide-react';

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, helperText, id, children, ...props }, ref) => {
    const generatedId = useId();
    const selectId = id || `select-${generatedId}`;
    const hasError = !!error;

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={selectId}
            className="block text-[11px] font-semibold uppercase tracking-wider text-zinc-500 mb-1"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select
            id={selectId}
            ref={ref}
            className={cn(
              'w-full px-3.5 py-2 bg-white border rounded-lg text-sm text-zinc-900',
              'focus:outline-none transition-all duration-150 shadow-xs appearance-none pr-9',
              hasError
                ? 'border-rose-500 focus:border-rose-500 focus:ring-2 focus:ring-rose-500/25'
                : 'border-zinc-200 focus:ring-2 focus:ring-emerald-600/25 focus:border-emerald-600',
              className
            )}
            {...props}
          >
            {children}
          </select>
          <ChevronDown
            size={14}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
          />
        </div>
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
Select.displayName = 'Select';

export { Select };
