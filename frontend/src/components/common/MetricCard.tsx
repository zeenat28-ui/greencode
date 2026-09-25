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
    <div className="card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="label mb-2">{title}</p>
          <p
            className="text-2xl font-black text-slate-900 leading-none truncate"
            style={accentColor ? { color: accentColor } : undefined}
          >
            {value}
          </p>
          {subtitle && (
            <p className="text-xs text-slate-500 mt-1.5 leading-tight">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="shrink-0 text-slate-300 mt-0.5">
            {icon}
          </div>
        )}
      </div>
    </div>
  );
}
