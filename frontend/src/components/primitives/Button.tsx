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
    'text-white bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-600 hover:to-emerald-800 active:from-emerald-700 active:to-emerald-800 ring-1 ring-inset ring-emerald-700/40 shadow-sm hover:shadow disabled:hover:shadow-sm',
  'primary-outline':
    'text-emerald-700 border border-emerald-200 hover:bg-emerald-50',
  secondary:
    'text-zinc-700 bg-white border border-zinc-200 hover:bg-zinc-50 hover:text-zinc-900 hover:border-zinc-300 shadow-sm',
  'secondary-outline':
    'text-zinc-600 border border-zinc-200 hover:bg-zinc-50 hover:text-zinc-900',
  ghost:
    'text-zinc-600 hover:text-zinc-900 hover:bg-zinc-100',
  dark:
    'text-white bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 shadow-sm ring-1 ring-inset ring-white/10',
  danger:
    'text-white bg-rose-600 hover:bg-rose-700 shadow-sm',
  'ghost-danger':
    'text-rose-600 hover:text-rose-700 hover:bg-rose-50',
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
