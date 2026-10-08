import { useState } from 'react';
import { 
  ShieldCheck, Copy, Check, X, GitPullRequest, Terminal, 
  ExternalLink, Code2, Sparkles 
} from 'lucide-react';

interface CiCdBadgeModalProps {
  isOpen: boolean;
  onClose: () => void;
  repoName?: string;
  score?: number;
}

export default function CiCdBadgeModal({
  isOpen,
  onClose,
  repoName = 'your-org/your-repo',
  score = 92,
}: CiCdBadgeModalProps) {
  const [copiedType, setCopiedType] = useState<string | null>(null);

  if (!isOpen) return null;

  const grade = score >= 80 ? 'Grade A' : score >= 65 ? 'Grade B' : 'Grade C';
  const badgeColor = score >= 80 ? '384C3B' : score >= 65 ? 'D97706' : 'E11D48';
  const encodedGrade = encodeURIComponent(`${score}/100 (${grade})`);
  
  const badgeMarkdown = `[![GreenCode SCI: ${score}/100](https://img.shields.io/badge/GreenCode%20SCI-${encodedGrade}-${badgeColor}?style=flat-square&logo=leaf&logoColor=white)](https://github.com/zeenat28-ui/greencode)`;
  
  const badgeHtml = `<a href="https://github.com/zeenat28-ui/greencode"><img src="https://img.shields.io/badge/GreenCode%20SCI-${encodedGrade}-${badgeColor}?style=flat-square&logo=leaf&logoColor=white" alt="GreenCode SCI: ${score}/100" /></a>`;

  const workflowYaml = `# .github/workflows/greencode-ci.yml
name: GreenCode Carbon & Energy Gate

on:
  push:
    branches: [ main, master ]
  pull_request:
    branches: [ main, master ]

jobs:
  sustainability-audit:
    runs-on: ubuntu-latest
    name: Audit Algorithmic Efficiency (SCI)
    steps:
      - name: Checkout Codebase
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Run GreenCode AST & Energy Gate
        run: |
          pip install greencode-cli
          greencode audit --path . --threshold 80 --fail-on-regression
        env:
          GREENCODE_API_KEY: \${{ secrets.GREENCODE_API_KEY }}
          AWS_BEDROCK_REGION: us-east-1
`;

  const copyToClipboard = (text: string, type: string) => {
    navigator.clipboard.writeText(text);
    setCopiedType(type);
    setTimeout(() => setCopiedType(null), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-7 h-7 rounded-lg bg-olive-700 flex items-center justify-center text-white">
              <ShieldCheck size={16} />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-white">
                CI/CD Gate &amp; Repository Badges
              </h3>
              <p className="text-[11px] text-slate-400">
                Automate algorithmic carbon audits in your GitHub Pull Requests
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-6 text-slate-800 max-h-[80vh] overflow-y-auto">
          {/* Badge Preview */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-2">
              Live README Badge Preview
            </label>
            <div className="p-4 rounded-lg bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
              <div className="inline-flex items-center shadow-sm rounded overflow-hidden">
                <span className="bg-slate-800 text-white text-xs font-semibold px-2.5 py-1 flex items-center gap-1 font-mono">
                  <span>🍃</span> GreenCode SCI
                </span>
                <span className="bg-olive-800 text-white text-xs font-bold px-2.5 py-1 font-mono">
                  {score}/100 ({grade})
                </span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => copyToClipboard(badgeMarkdown, 'markdown')}
                  className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                >
                  {copiedType === 'markdown' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  {copiedType === 'markdown' ? 'Copied Markdown' : 'Copy Markdown'}
                </button>
                <button
                  onClick={() => copyToClipboard(badgeHtml, 'html')}
                  className="btn-secondary text-xs px-2.5 py-1 flex items-center gap-1.5"
                >
                  {copiedType === 'html' ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                  {copiedType === 'html' ? 'Copied HTML' : 'Copy HTML'}
                </button>
              </div>
            </div>
          </div>

          {/* GitHub Actions Workflow */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 flex items-center gap-1.5">
                <GitPullRequest size={13} className="text-olive-700" />
                GitHub Actions Quality Gate Workflow (.github/workflows/greencode-ci.yml)
              </label>
              <button
                onClick={() => copyToClipboard(workflowYaml, 'yaml')}
                className="btn-primary text-xs px-2.5 py-1 flex items-center gap-1.5 bg-olive-700 hover:bg-olive-800"
              >
                {copiedType === 'yaml' ? <Check size={12} /> : <Copy size={12} />}
                {copiedType === 'yaml' ? 'Copied Workflow' : 'Copy Workflow YAML'}
              </button>
            </div>
            <div className="relative rounded-lg bg-slate-900 border border-slate-800 overflow-hidden text-xs font-mono text-slate-200">
              <pre className="p-4 overflow-x-auto leading-relaxed">
                <code>{workflowYaml}</code>
              </pre>
            </div>
          </div>

          {/* Feature explanations */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
            <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 space-y-1">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <Terminal size={13} className="text-olive-700" />
                Deterministic Quality Gate
              </div>
              <p className="text-slate-500 leading-relaxed text-[11px]">
                Blocks pull requests that introduce algorithmic regressions or nested quadratic loops below your threshold.
              </p>
            </div>

            <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 space-y-1">
              <div className="font-bold text-slate-800 flex items-center gap-1.5">
                <Code2 size={13} className="text-olive-700" />
                Automated Diff Comments
              </div>
              <p className="text-slate-500 leading-relaxed text-[11px]">
                Posts an automated PR comment comparing Joules and carbon footprint before and after the code change.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

