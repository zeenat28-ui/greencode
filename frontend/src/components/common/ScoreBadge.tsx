interface ScoreBadgeProps {
  score: number;
  size?: 'sm' | 'md' | 'lg';
}

export default function ScoreBadge({ score, size = 'md' }: ScoreBadgeProps) {
  const grade =
    score >= 90 ? 'A+' :
    score >= 80 ? 'A'  :
    score >= 70 ? 'B'  :
    score >= 60 ? 'C'  : 'F';

  const strokeColor =
    score >= 80 ? '#22c55e' :
    score >= 60 ? '#d97706' : '#dc2626';

  const dim   = size === 'lg' ? 120 : size === 'md' ? 80 : 56;
  const r     = (dim - 10) / 2;
  const circ  = 2 * Math.PI * r;
  const dash  = (score / 100) * circ;
  const gap   = circ - dash;

  const fontSize =
    size === 'lg' ? 22 :
    size === 'md' ? 15 : 11;

  const subSize =
    size === 'lg' ? 10 :
    size === 'md' ? 8  : 7;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} className="-rotate-90">
        <circle
          cx={dim / 2} cy={dim / 2} r={r}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth={size === 'lg' ? 7 : 5}
        />
        <circle
          cx={dim / 2} cy={dim / 2} r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth={size === 'lg' ? 7 : 5}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${gap}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-extrabold leading-none"
          style={{ color: strokeColor, fontSize }}
        >
          {Math.round(score)}
        </span>
        <span className="font-semibold text-slate-500 leading-none" style={{ fontSize: subSize }}>
          {grade}
        </span>
      </div>
    </div>
  );
}
