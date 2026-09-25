import { Severity, ViolationType, VIOLATION_LABEL_MAP, VIOLATION_RULE_MAP } from '../../types';

interface SeverityBadgeProps {
  severity: Severity;
}

const SEV_STYLES: Record<Severity, string> = {
  CRITICAL: 'badge badge-critical',
  HIGH:     'badge badge-high',
  MEDIUM:   'badge badge-medium',
  LOW:      'badge badge-low',
};

function SeverityBadge({ severity }: SeverityBadgeProps) {
  return (
    <span className={SEV_STYLES[severity] ?? 'badge badge-low'}>
      {severity}
    </span>
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
    <div
      onClick={onClick}
      className={`card p-4 cursor-pointer transition-all duration-150 ${
        isSelected
          ? 'border-mint-500 ring-2 ring-mint-100 shadow-md'
          : 'hover:border-slate-300 hover:shadow-md'
      }`}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3 mb-2.5">
        <div className="flex flex-wrap items-center gap-1.5">
          <SeverityBadge severity={violation.severity} />
          <code className="px-1.5 py-0.5 bg-slate-100 text-slate-600 rounded text-xs font-mono font-bold">
            {ruleCode}
          </code>
          {violation.language && (
            <span className="px-1.5 py-0.5 bg-mint-50 text-mint-700 border border-mint-200 rounded text-xs font-semibold">
              {violation.language}
            </span>
          )}
        </div>
        <span className="text-xs font-bold text-red-500 shrink-0">
          -{violation.deduction} pts
        </span>
      </div>

      {/* Title */}
      <h3 className="font-bold text-sm text-slate-900 mb-1">{label}</h3>

      {/* Description */}
      <p className="text-xs text-slate-500 mb-2.5 line-clamp-2 leading-relaxed">
        {violation.description}
      </p>

      {/* Location row */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 mb-2.5 font-mono">
        <span>{violation.relative_path || violation.file_path}</span>
        <span>Line {violation.line_number}</span>
        {violation.gsf_pattern && (
          <span className="font-sans text-slate-400">{violation.gsf_pattern}</span>
        )}
      </div>

      {/* Code snippet */}
      {violation.snippet && (
        <pre className="bg-[#f8f9fa] border border-slate-200 rounded-lg p-3 text-xs font-mono text-slate-600 overflow-x-auto mb-2.5 leading-relaxed">
          {violation.snippet}
        </pre>
      )}

      {/* Suggested fix */}
      {violation.suggested_fix && (
        <div className="flex items-start gap-2 p-2.5 bg-mint-50 rounded-lg border border-mint-100">
          <span className="text-mint-600 font-bold text-xs shrink-0 mt-px">Fix</span>
          <span className="text-xs text-slate-600 leading-relaxed">{violation.suggested_fix}</span>
        </div>
      )}
    </div>
  );
}

export default SeverityBadge;
