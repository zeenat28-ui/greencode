import { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: ReactNode;
  accentColor?: string;
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  accentColor,
}: MetricCardProps) {
  return (
    <div className="card p-3">
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <span className="text-xs font-medium text-[var(--gc-text-tertiary)] truncate">{title}</span>
        {icon && (
          <div className="shrink-0 w-6 h-6 rounded-md bg-[var(--gc-bg-subtle)] border border-[var(--gc-border-default)] flex items-center justify-center text-[var(--gc-text-secondary)]">
            {icon}
          </div>
        )}
      </div>
      <p
        className="text-xl font-semibold font-mono tracking-tight text-[var(--gc-text-primary)] leading-none truncate"
        style={accentColor ? { color: accentColor } : undefined}
      >
        {value}
      </p>
      {subtitle && (
        <p className="text-[11px] text-[var(--gc-text-tertiary)] mt-1.5 leading-tight truncate">{subtitle}</p>
      )}
    </div>
  );
}
