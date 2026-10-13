import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export type BadgeVariant =
  | 'default'
  | 'olive'
  | 'critical'
  | 'high'
  | 'medium'
  | 'low'
  | 'success'
  | 'warning'
  | 'info'
  | 'outline';

export type BadgeSize = 'sm' | 'md';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  size?: BadgeSize;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: 'bg-zinc-100 text-zinc-700 border border-zinc-200',
  olive: 'bg-emerald-50 text-emerald-800 border border-emerald-200/80',
  critical: 'bg-rose-50 text-rose-700 border border-rose-200',
  high: 'bg-amber-50 text-amber-800 border border-amber-200',
  medium: 'bg-zinc-100 text-zinc-700 border border-zinc-200',
  low: 'bg-zinc-50 text-zinc-500 border border-zinc-200',
  success: 'bg-emerald-50 text-emerald-800 border border-emerald-200',
  warning: 'bg-amber-50 text-amber-800 border border-amber-200',
  info: 'bg-blue-50 text-blue-700 border border-blue-200',
  outline: 'bg-transparent text-zinc-600 border border-zinc-200',
};

const sizeClasses: Record<BadgeSize, string> = {
  sm: 'px-1.5 py-0.5 text-[10px]',
  md: 'px-2 py-0.5 text-[11px]',
};

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  ({ className, variant = 'default', size = 'md', children, ...props }, ref) => (
    <span
      ref={ref}
      className={cn(
        'inline-flex items-center gap-1 rounded-md font-mono font-semibold leading-none',
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {children}
    </span>
  )
);
Badge.displayName = 'Badge';

export { Badge };
export const badgeVariants = { variantClasses, sizeClasses };
