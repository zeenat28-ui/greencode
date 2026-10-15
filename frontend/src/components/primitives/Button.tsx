import { cloneElement, forwardRef } from 'react';
import { ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

export type ButtonVariant =
  | 'primary'
  | 'primary-outline'
  | 'secondary'
  | 'secondary-outline'
  | 'ghost'
  | 'dark'
  | 'danger'
  | 'ghost-danger'
  | 'link';

export type ButtonSize = 'xs' | 'sm' | 'md' | 'lg' | 'xl';

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  asChild?: boolean;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'text-white bg-emerald-600 hover:bg-emerald-700',
  'primary-outline':
    'text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800 hover:bg-emerald-50 dark:hover:bg-emerald-950',
  secondary:
    'text-[var(--gc-text-primary)] bg-[var(--gc-bg-default)] border border-[var(--gc-border-default)] hover:bg-[var(--gc-bg-subtle)]',
  'secondary-outline':
    'text-[var(--gc-text-secondary)] border border-[var(--gc-border-default)] hover:bg-[var(--gc-bg-subtle)]',
  ghost:
    'text-[var(--gc-text-secondary)] hover:text-[var(--gc-text-primary)] hover:bg-[var(--gc-bg-subtle)]',
  dark:
    'bg-[var(--gc-text-primary)] text-[var(--gc-bg-default)] hover:opacity-90',
  danger:
    'text-white bg-rose-600 hover:bg-rose-700',
  'ghost-danger':
    'text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950',
  link:
    'text-emerald-600 hover:text-emerald-800 underline-offset-2 hover:underline p-0 shadow-none ring-0',
};

const sizeClasses: Record<ButtonSize, string> = {
  xs: 'px-2.5 py-1 text-xs',
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
  xl: 'px-6 py-3 text-base',
};

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'primary', size = 'md', asChild = false, children, ...props }, ref) => {
    const classes = cn(
      'inline-flex items-center justify-center gap-2 rounded-lg font-medium text-sm transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50',
      variantClasses[variant],
      sizeClasses[size],
      className
    );

    if (asChild) {
      const child = children as React.ReactElement;
      return cloneElement(child, {
        className: cn(classes, (child.props as any).className),
        ...props,
      } as any);
    }

    return (
      <button type="button" className={classes} ref={ref} {...props}>
        {children}
      </button>
    );
  }
);
Button.displayName = 'Button';

export { Button };
