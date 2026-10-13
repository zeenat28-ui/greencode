import { Severity, ViolationType, VIOLATION_LABEL_MAP, VIOLATION_RULE_MAP } from '../../types';
import { Badge } from '../primitives/Badge';
import type { BadgeVariant } from '../primitives/Badge';
import { Card } from '../primitives/Card';
import { cn } from '../../lib/utils';

const SEVERITY_BADGE_VARIANT: Record<Severity, BadgeVariant> = {
  CRITICAL: 'critical',
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

function SeverityBadge({ severity }: { severity: Severity }) {
  return (
    <Badge variant={SEVERITY_BADGE_VARIANT[severity] ?? 'low'}>
      {severity}
    </Badge>
  );
}

interface IssueCardProps {
  violation: any;
  onClick?: () => void;
  isSelected?: boolean;
}

export function IssueCard({ violation, onClick, isSelected = false }: IssueCardProps) {
  const ruleCode = VIOLATION_RULE_MAP[violation.violation_type] || 'GSF-S999';
  const label    = VIOLATION_LABEL_MAP[violation.violation_type as ViolationType] || violation.title;

  return (
    <Card
      onClick={onClick}
      variant="default"
      padding="md"
      className={cn(
        'cursor-pointer overflow-hidden max-w-full',
        isSelected
          ? 'border-zinc-900 ring-1 ring-zinc-900/10 shadow-sm'
          : 'hover:border-zinc-300'
      )}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityBadge severity={violation.severity} />
          <code className="px-1.5 py-0.5 bg-zinc-100 text-zinc-700 rounded text-[11px] font-mono font-semibold border border-zinc-200/80">
            {ruleCode}
          </code>
          {violation.language && (
            <Badge variant="olive" size="sm" className="text-[11px] px-1.5 py-0.5 font-medium">
              {violation.language}
            </Badge>
          )}
        </div>
        <span className="text-xs font-mono font-semibold text-rose-600 shrink-0">
          -{violation.deduction} pts
        </span>
      </div>

      {/* Title */}
      <h3 className="font-semibold text-sm text-zinc-950 mb-1">{label}</h3>

      {/* Description */}
      <p className="text-xs text-zinc-600 mb-2.5 leading-relaxed">
        {violation.description}
      </p>

      {/* Location row */}
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-zinc-500 mb-2.5 font-mono">
        <span className="text-zinc-800 font-medium">{violation.relative_path || violation.file_path}:{violation.line_number}</span>
        {violation.gsf_pattern && (
          <>
            <span>&middot;</span>
            <span className="font-sans text-zinc-500">{violation.gsf_pattern}</span>
          </>
        )}
      </div>

      {/* Code snippet */}
      {violation.snippet && (
        <pre className="bg-[#0D1117] border border-zinc-800 rounded-lg p-3 text-xs font-mono text-zinc-200 overflow-x-auto mb-2.5 leading-relaxed">
          {violation.snippet}
        </pre>
      )}

      {/* Suggested fix */}
      {violation.suggested_fix && (
        <div className="flex items-start gap-2 p-2.5 bg-emerald-50/60 rounded-lg border border-emerald-200/80">
          <span className="text-emerald-800 font-mono font-semibold text-[11px] shrink-0 mt-px">Remediation:</span>
          <span className="text-xs text-zinc-700 leading-relaxed">{violation.suggested_fix}</span>
        </div>
      )}
      </Card>
    );
  }

export default SeverityBadge;
