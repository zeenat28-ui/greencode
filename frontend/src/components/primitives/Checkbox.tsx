import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export interface CheckboxProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  description?: string;
}

export const Checkbox = forwardRef<HTMLInputElement, CheckboxProps>(
  ({ className, label, description, ...props }, ref) => {
    if (label) {
      return (
        <label className="flex items-start gap-2.5 cursor-pointer text-sm">
          <input
            type="checkbox"
            ref={ref}
            className={cn(
              'mt-0.5 w-4 h-4 text-emerald-600 rounded border-zinc-300',
              'focus:ring-2 focus:ring-emerald-500/25',
              className
            )}
            {...props}
          />
          <div className="flex flex-col">
            <span className="text-sm font-medium text-zinc-900">{label}</span>
            {description && <span className="text-[11px] text-zinc-500">{description}</span>}
          </div>
        </label>
      );
    }
    return (
      <input
        type="checkbox"
        ref={ref}
        className={cn(
          'w-4 h-4 text-emerald-600 rounded border-zinc-300',
          'focus:ring-2 focus:ring-emerald-500/25',
          className
        )}
        {...props}
      />
    );
  }
);
Checkbox.displayName = 'Checkbox';
