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
    <div className="card p-4 hover:border-zinc-300 transition-colors">
      <div className="flex items-center justify-between gap-2 mb-2">
        <span className="text-xs font-medium text-zinc-500 truncate">{title}</span>
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
    </div>
  );
}
