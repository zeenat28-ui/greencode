import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export type ProgressVariant = 'emerald' | 'amber' | 'rose' | 'zinc';
export type ProgressSize = 'sm' | 'md' | 'lg';

export interface ProgressRingProps extends React.HTMLAttributes<HTMLDivElement> {
  score: number;
  threshold: number;
  size?: number;
  variant?: ProgressVariant;
  showLabel?: boolean;
  sizeToken?: ProgressSize;
}

const variantColors: Record<ProgressVariant, string> = {
  emerald: '#059669',
  amber: '#d97706',
  rose: '#e11d48',
  zinc: '#52525b',
};

export const ProgressRing = forwardRef<HTMLDivElement, ProgressRingProps>(
  (
    { className, score, threshold, size: sizePx, variant, showLabel = true, sizeToken = 'md', ...props },
    ref
  ) => {
    const pct = Math.max(0, Math.min(100, Math.round(score)));
    const isPass = pct >= threshold;
    const color = variant ? variantColors[variant] : isPass ? variantColors.emerald : variantColors.rose;

    const sizeMap: Record<ProgressSize, number> = { sm: 52, md: 72, lg: 96 };
    const dim = sizePx ?? sizeMap[sizeToken];
    const strokeWidth = dim <= 60 ? 5 : dim <= 80 ? 5 : 6;
    const r = (dim - strokeWidth * 2) / 2;
    const circ = 2 * Math.PI * r;
    const dash = (pct / 100) * circ;
    const gap = circ - dash;

    return (
      <div
        ref={ref}
        className={cn('relative inline-flex items-center justify-center', className)}
        style={{ width: dim, height: dim }}
        {...props}
      >
        <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} className="-rotate-90">
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            fill="none"
            stroke="#f4f4f5"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={dim / 2}
            cy={dim / 2}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={`${dash} ${gap}`}
            style={{ transition: 'stroke-dasharray 0.6s ease' }}
          />
        </svg>
        {showLabel && (
          <div className="absolute inset-0 flex flex-col items-center justify-center">
            <span
              className="font-mono font-bold leading-none"
              style={{ color, fontSize: dim <= 60 ? 11 : dim <= 80 ? 14 : 20 }}
            >
              {pct}
            </span>
          </div>
        )}
      </div>
    );
  }
);
ProgressRing.displayName = 'ProgressRing';
