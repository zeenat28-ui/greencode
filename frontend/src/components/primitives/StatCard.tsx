import { forwardRef } from 'react';
import { cn } from '../../lib/utils';
import type { LucideIcon } from 'lucide-react';

export interface StatCardProps extends React.HTMLAttributes<HTMLDivElement> {
  label: string;
  value: string | number;
  icon?: React.ReactNode;
  iconFg?: LucideIcon;
  accentColor?: string;
  subtitle?: string;
  trend?: { direction: 'up' | 'down'; value: string };
  loading?: boolean;
}

export const StatCard = forwardRef<HTMLDivElement, StatCardProps>(
  (
    { className, label, value, icon, iconFg: Icon, accentColor, subtitle, trend, loading },
    ref
  ) => {
    return (
      <div
        ref={ref}
        className={cn(
          'card p-4 hover:border-zinc-300 transition-colors',
          loading && 'animate-pulse opacity-70',
          className
        )}
      >
        <div className="flex items-center justify-between gap-2 mb-2">
          <span className="text-xs font-medium text-zinc-500 truncate">{label}</span>
          {Icon && (
            <div className="shrink-0 w-7 h-7 rounded-lg bg-zinc-50 border border-zinc-200/70 flex items-center justify-center text-zinc-600">
              <Icon size={15} />
            </div>
          )}
          {icon && (
            <div className="shrink-0 w-7 h-7 rounded-lg bg-zinc-50 border border-zinc-200/70 flex items-center justify-center text-zinc-600">
              {icon}
            </div>
          )}
        </div>
        <p
          className="text-2xl font-semibold font-mono tracking-tight text-zinc-950 leading-none truncate"
          style={accentColor ? { color: accentColor } : undefined}
        >
          {value}
        </p>
        {subtitle && (
          <p className="text-[11px] text-zinc-500 mt-2 leading-tight truncate">{subtitle}</p>
        )}
        {trend && (
          <div
            className={cn(
              'flex items-center gap-1 mt-2 text-[11px] font-mono',
              trend.direction === 'up' ? 'text-emerald-700' : 'text-rose-700'
            )}
          >
            {Icon && <Icon size={10} />}
            <span>{trend.value}</span>
          </div>
        )}
      </div>
    );
  }
);
StatCard.displayName = 'StatCard';
