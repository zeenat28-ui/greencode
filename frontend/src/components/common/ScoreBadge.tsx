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
    score >= 80 ? '#059669' :
    score >= 60 ? '#d97706' : '#e11d48';

  const dim   = size === 'lg' ? 96 : size === 'md' ? 72 : 52;
  const r     = (dim - 10) / 2;
  const circ  = 2 * Math.PI * r;
  const dash  = (score / 100) * circ;
  const gap   = circ - dash;

  const fontSize =
    size === 'lg' ? 20 :
    size === 'md' ? 14 : 11;

  const subSize =
    size === 'lg' ? 10 :
    size === 'md' ? 8  : 7;

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: dim, height: dim }}>
      <svg width={dim} height={dim} viewBox={`0 0 ${dim} ${dim}`} className="-rotate-90">
        <circle
          cx={dim / 2} cy={dim / 2} r={r}
          fill="none"
          stroke="#f4f4f5"
          strokeWidth={size === 'lg' ? 6 : 5}
        />
        <circle
          cx={dim / 2} cy={dim / 2} r={r}
          fill="none"
          stroke={strokeColor}
          strokeWidth={size === 'lg' ? 6 : 5}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${gap}`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="font-mono font-bold leading-none"
          style={{ color: strokeColor, fontSize }}
        >
          {Math.round(score)}
        </span>
        <span className="font-mono font-semibold text-zinc-400 leading-none mt-0.5" style={{ fontSize: subSize }}>
          {grade}
        </span>
      </div>
    </div>
  );
}
