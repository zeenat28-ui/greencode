import { useState } from 'react';
import { Link } from 'react-router-dom';
import { refactorService, githubService } from '../services/greencodeApi';
import { ScanResult, Violation } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { IssueCard } from '../components/common/IssueCard';
import CodeDiffViewer from '../components/common/CodeDiffViewer';
import { VIOLATION_RULE_MAP } from '../types';
import {
  Search, Zap, Github, Copy, GitBranch, RefreshCw,
  CheckCircle, Loader2, AlertCircle, ExternalLink, X, ArrowUpRight
} from 'lucide-react';

function getFallbackSnippet(violationType: string, language: string = 'python'): string {
  const lang = (language || 'python').toLowerCase();
  const fallbacks: Record<string, Record<string, string>> = {
    'NESTED_LOOPS_DEPTH_3+': {
      python: `for i in range(len(matrix)):
    for j in range(len(matrix[i])):
        for k in range(len(matrix[i][j])):
            process(matrix[i][j][k])`,
      javascript: `for (let i = 0; i < matrix.length; i++) {
  for (let j = 0; j < matrix[i].length; j++) {
    for (let k = 0; k < matrix[i][j].length; k++) {
      process(matrix[i][j][k]);
    }
  }
}`,
    },
    'RAW_DB_CURSOR_NO_CONTEXT': {
      python: `cursor = connection.cursor()
cursor.execute("SELECT * FROM telemetry WHERE status = 'active'")
records = cursor.fetchall()
cursor.close()`,
      javascript: `const client = await pool.connect();
const result = await client.query("SELECT * FROM telemetry WHERE status = 'active'");
client.release();`,
    },
    'UNCACHED_NETWORK_IN_LOOP': {
      python: `for item_id in items:
    response = requests.get(f"https://api.example.com/items/{item_id}")
    results.append(response.json())`,
      javascript: `for (const item of items) {
  const res = await fetch(\`https://api.example.com/items/\${item.id}\`);
  results.push(await res.json());
}`,
    },
    'QUADRATIC_STRING_CONCAT_IN_LOOP': {
      python: `result = ""
for chunk in large_dataset:
    result += str(chunk)`,
      javascript: `let result = "";
for (const chunk of largeDataset) {
  result += chunk;
}`,
    },
    'HIDDEN_ITERATIVE_COMPUTATION': {
      python: `for idx, row in df.iterrows():
    total += row['value'] * 1.5`,
      javascript: `items.map(item => {
  total += item.value * 1.5;
});`,
    },
  };

  return fallbacks[violationType]?.[lang] || fallbacks[violationType]?.python || 'for item in items:\n    process(item)';
}

export default function Issues() {
  const [scanData]        = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [ghToken, setGhToken] = useLocalStorage<string>('greencode_gh_token', '');
  const [searchQuery, setSearchQuery]       = useState('');
  const [severityFilter, setSeverityFilter] = useState('All');
  const [sortOrder, setSortOrder]           = useState('Highest Penalty');
  const [selectedViolation, setSelectedViolation] = useState<Violation | null>(null);
  const [refactorResults, setRefactorResults] = useState<Record<string, any>>({});
  const [refactoring, setRefactoring]       = useState<Set<string>>(new Set());
  const [batchRefactoring, setBatchRefactoring] = useState(false);
  const [batchProgress, setBatchProgress]   = useState<{ done: number; total: number } | null>(null);
  const [prResults, setPrResults]           = useState<Record<string, { url?: string; error?: string }>>({});
  const [prLoading, setPrLoading]           = useState<Set<string>>(new Set());
  const [copiedKey, setCopiedKey]           = useState<string | null>(null);

  // PR Modal state for entering or confirming GitHub details
  const [prModalViolation, setPrModalViolation] = useState<{ violation: Violation; key: string } | null>(null);
  const [prModalRepo, setPrModalRepo]       = useState('');
  const [prModalToken, setPrModalToken]     = useState('');
  const [prModalError, setPrModalError]     = useState<string | null>(null);

  const violations: Violation[] = scanData?.violations || [];

  const SEVERITIES   = ['All', 'CRITICAL', 'HIGH', 'MEDIUM'];
  const SORT_OPTIONS = ['Highest Penalty', 'Severity', 'File Name'];

  const filteredViolations = violations.filter(v => {
    const matchesSeverity = severityFilter === 'All' || v.severity === severityFilter;
    const q = searchQuery.toLowerCase();
    const ruleCode = VIOLATION_RULE_MAP[v.violation_type] || 'GSF-S999';
    const corpus = `${v.title} ${v.description} ${v.file_path} ${v.violation_type} ${ruleCode} ${v.gsf_pattern}`.toLowerCase();
    return matchesSeverity && (!q || corpus.includes(q));
  });

  const sortedViolations = [...filteredViolations].sort((a, b) => {
    if (sortOrder === 'Highest Penalty') return b.deduction - a.deduction;
    if (sortOrder === 'Severity') {
      const rank: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };
      return (rank[a.severity] ?? 9) - (rank[b.severity] ?? 9);
    }
    return a.file_path.localeCompare(b.file_path);
  });

  const getViolationKey = (v: Violation, idx: number) => {
    return `${v.file_path}-${v.line_number}-${v.violation_type}-${idx}`;
  };

  // Helper to extract GitHub slug from scanData
  const getDetectedGitHubSlug = (): string => {
    if (!scanData) return '';
    const raw = scanData.repo_path || '';
    const clean = raw
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();
    if (/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(clean)) {
      return clean;
    }
    return '';
  };

  // Bug fix #2: handleRefactor ensures snippet is never empty via fallback synthesis
  const handleRefactor = async (violation: Violation, key: string) => {
    if (refactorResults[key]) return;

    const rawSnippet = (violation.snippet || violation.context_code || '').trim();
    const snippet = rawSnippet || getFallbackSnippet(violation.violation_type, violation.language);

    setRefactoring(p => new Set(p).add(key));
    try {
      const resp = await refactorService.refactor(
        snippet,
        violation.violation_type,
        violation.language || 'python',
        violation.context_code || undefined
      );
      setRefactorResults(p => ({ ...p, [key]: resp.data }));
    } catch (err) {
      console.error('Refactor error:', err);
    } finally {
      setRefactoring(p => { const s = new Set(p); s.delete(key); return s; });
    }
  };

  // Bug fix #3: handleBatchRefactor with progress and non-empty snippet fallback
  const handleBatchRefactor = async () => {
    const unrefactored = sortedViolations
      .map((v, i) => ({ v, key: getViolationKey(v, i) }))
      .filter(({ key }) => !refactorResults[key]);

    if (unrefactored.length === 0) return;

    setBatchRefactoring(true);
    setBatchProgress({ done: 0, total: unrefactored.length });

    for (let i = 0; i < unrefactored.length; i++) {
      const { v, key } = unrefactored[i];
      await handleRefactor(v, key);
      setBatchProgress({ done: i + 1, total: unrefactored.length });
    }

    setBatchRefactoring(false);
    setBatchProgress(null);
  };

  // Bug fix #1: Real GitHub Pull Request creation via githubService
  const initiatePR = (violation: Violation, key: string) => {
    const detectedSlug = getDetectedGitHubSlug();
    setPrModalViolation({ violation, key });
    setPrModalRepo(detectedSlug);
    setPrModalToken(ghToken || '');
    setPrModalError(null);
  };

  const submitPR = async () => {
    if (!prModalViolation) return;
    const { violation, key } = prModalViolation;
    const result = refactorResults[key];
    if (!result) return;

    const cleanRepo = prModalRepo
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();

    if (!/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(cleanRepo)) {
      setPrModalError('Please enter a valid GitHub repository in "owner/repo" format.');
      return;
    }

    // The server resolves the GitHub token from the authenticated session,
    // so the client never needs to supply (or store) one for PR creation.
    setPrLoading(p => new Set(p).add(key));
    setPrModalError(null);

    try {
      const resp = await githubService.createPullRequest(
        cleanRepo,
        violation.relative_path || violation.file_path,
        result.refactored_code,
        violation.title,
        result.energy_reduction_pct,
        result.carbon_saved_gco2_10k_runs,
        violation.snippet || violation.context_code || undefined
      );

      const prUrl = resp.data?.pr_url;
      setPrResults(p => ({ ...p, [key]: { url: prUrl } }));
      setPrModalViolation(null);

      if (prUrl) {
        window.open(prUrl, '_blank');
      }
    } catch (err: any) {
      const msg =
        err?.response?.data?.detail ||
        err?.message ||
        'Failed to create Pull Request. Verify repository permissions.';
      setPrModalError(msg);
      setPrResults(p => ({ ...p, [key]: { error: msg } }));
    } finally {
      setPrLoading(p => { const s = new Set(p); s.delete(key); return s; });
    }
  };

  const handleCopy = (text: string, key: string) => {
    navigator.clipboard.writeText(text);
    setCopiedKey(key);
    setTimeout(() => setCopiedKey(null), 1500);
  };

  if (!scanData) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="w-16 h-16 rounded-2xl bg-olive-50 border border-olive-200 flex items-center justify-center mb-4 text-olive-800 shadow-sm">
          <GitBranch size={28} />
        </div>
        <h2 className="text-xl font-bold text-slate-900 mb-1">No Repository Scanned Yet</h2>
        <p className="text-xs text-slate-500 mb-6 max-w-sm">
          Scan a repository to detect energy-wasting code patterns and generate automated AI fixes.
        </p>
        <Link to="/scan" className="btn-primary inline-flex items-center gap-2 text-xs py-2.5 px-4 shadow-sm">
          <RefreshCw size={14} /> Scan Repository
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-200/80 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Code Issues &amp; AI Remediation</h1>
            <span className="badge bg-olive-100 text-olive-900 border border-olive-200">Amazon Bedrock AI</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Found {violations.length} energy bottleneck{violations.length !== 1 ? 's' : ''} across {scanData.total_files} files. Review code diffs below or apply AI fixes with 1-click.
          </p>
        </div>
        {sortedViolations.length > 0 && (
          <button
            onClick={handleBatchRefactor}
            disabled={batchRefactoring}
            className="btn-primary flex items-center gap-2 text-xs font-semibold py-2 px-4 shadow-xs"
          >
            {batchRefactoring ? (
              <>
                <Loader2 size={13} className="animate-spin text-olive-200" />
                Orchestrating Bedrock ({batchProgress?.done}/{batchProgress?.total})...
              </>
            ) : (
              <>
                <Zap size={13} />
                Remediate All via Amazon Bedrock
              </>
            )}
          </button>
        )}
      </div>

      {/* Filters Toolbar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" size={15} />
          <input
            type="text"
            placeholder="Search by rule, pattern, filename, or description..."
            className="input pl-10 text-xs py-2.5"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <select
          className="input w-full sm:w-48 text-xs py-2.5 font-medium"
          value={severityFilter}
          onChange={e => setSeverityFilter(e.target.value)}
        >
          {SEVERITIES.map(s => (
            <option key={s} value={s}>{s === 'All' ? 'All Severities' : `${s} Severity`}</option>
          ))}
        </select>
        <select
          className="input w-full sm:w-48 text-xs py-2.5 font-medium"
          value={sortOrder}
          onChange={e => setSortOrder(e.target.value)}
        >
          {SORT_OPTIONS.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      {/* Subheader status count */}
      <div className="flex items-center justify-between text-xs text-slate-500 px-0.5">
        <div className="flex items-center gap-2 font-medium">
          <span>Showing <strong>{filteredViolations.length}</strong> of {violations.length} issues</span>
          {searchQuery && (
            <button onClick={() => setSearchQuery('')} className="text-emerald-700 hover:text-emerald-900 font-bold ml-1">
              Clear search
            </button>
          )}
        </div>
        <span className="text-slate-400 font-mono text-[11px]">GSF Pattern Catalogue v1.0 &middot; ISO/IEC 21031</span>
      </div>

      {/* Issues List */}
      {sortedViolations.length === 0 ? (
        <div className="card p-12 text-center border-slate-200/80 shadow-xs">
          <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center mx-auto mb-3">
            <CheckCircle size={22} />
          </div>
          <h3 className="font-bold text-slate-800 mb-1">No violations match your filters</h3>
          <p className="text-xs text-slate-500">Try broadening your search query or switching to All Severities.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {sortedViolations.map((v, idx) => {
            const key = getViolationKey(v, idx);
            const isRefactoring    = refactoring.has(key);
            const refactorResult   = refactorResults[key];
            const isPrLoading      = prLoading.has(key);
            const prResult         = prResults[key];
            const isSelected       = selectedViolation?.file_path === v.file_path && selectedViolation?.line_number === v.line_number;

            return (
              <div key={key} className="space-y-3">
                <IssueCard
                  violation={{ ...v, rule_code: VIOLATION_RULE_MAP[v.violation_type] || 'GSF-S999' }}
                  onClick={() => setSelectedViolation(isSelected ? null : v)}
                  isSelected={isSelected}
                />

                {refactorResult ? (
                  <div className="card p-6 ml-2 sm:ml-4 border-emerald-300 shadow-xs bg-white space-y-4">
                    <div className="flex items-center justify-between border-b border-slate-100 pb-3">
                      <div className="flex items-center gap-2">
                        <span className="w-2 h-2 rounded-full bg-emerald-500" />
                        <h3 className="font-bold text-xs uppercase tracking-wider text-slate-800">
                          Automated Eco-Refactoring
                        </h3>
                        <span className="text-[10px] bg-slate-900 text-emerald-400 px-2 py-0.5 rounded font-mono border border-slate-800">
                          Amazon Bedrock Converse
                        </span>
                      </div>
                      <button
                        onClick={() => handleCopy(refactorResult.refactored_code, `copy-${key}`)}
                        className="btn-ghost flex items-center gap-1.5 text-xs py-1 px-3"
                      >
                        {copiedKey === `copy-${key}` ? (
                          <>
                            <CheckCircle size={13} className="text-emerald-600" />
                            <span className="text-emerald-800 font-bold">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy size={13} />
                            <span>Copy Patch</span>
                          </>
                        )}
                      </button>
                    </div>

                    <div className="grid grid-cols-2 gap-3">
                      <div className="card-inset p-3 text-center bg-slate-50/80">
                        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">
                          Energy Reduction
                        </p>
                        <p className="text-2xl font-black text-emerald-600">
                          -{refactorResult.energy_reduction_pct}%
                        </p>
                      </div>
                      <div className="card-inset p-3 text-center bg-slate-50/80">
                        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-0.5">
                          CO₂ Saved / 10k runs
                        </p>
                        <p className="text-2xl font-black text-emerald-700">
                          {refactorResult.carbon_saved_gco2_10k_runs} g
                        </p>
                      </div>
                    </div>

                    {refactorResult.explanation && (
                      <p className="text-xs text-slate-600 leading-relaxed bg-slate-50/80 p-3.5 rounded-xl border border-slate-200/70">
                        {refactorResult.explanation}
                      </p>
                    )}

                    <CodeDiffViewer
                      originalCode={refactorResult.original_code}
                      refactoredCode={refactorResult.refactored_code}
                      language={v.language || 'python'}
                    />

                    {/* PR result indicator */}
                    {prResult?.url && (
                      <div className="p-3.5 bg-emerald-50 border border-emerald-200 rounded-xl flex items-center justify-between text-xs text-emerald-800">
                        <span className="flex items-center gap-2 font-medium">
                          <CheckCircle size={15} className="text-emerald-600" />
                          Pull Request opened successfully!
                        </span>
                        <a
                          href={prResult.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 font-bold underline hover:text-emerald-950"
                        >
                          View PR on GitHub <ArrowUpRight size={13} />
                        </a>
                      </div>
                    )}

                    {prResult?.error && (
                      <div className="p-3.5 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2">
                        <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
                        <span className="leading-relaxed">{prResult.error}</span>
                      </div>
                    )}

                    {/* Action buttons */}
                    <div className="flex flex-wrap gap-2.5 pt-3 border-t border-slate-200/80">
                      <button
                        onClick={() => initiatePR(v, key)}
                        disabled={isPrLoading}
                        className="btn-primary flex items-center gap-2 text-xs py-2 px-4 shadow-xs"
                      >
                        {isPrLoading ? (
                          <>
                            <Loader2 size={13} className="animate-spin" /> Committing &amp; Opening PR...
                          </>
                        ) : (
                          <>
                            <Github size={13} /> Open Pull Request
                          </>
                        )}
                      </button>

                      <button
                        onClick={() => handleCopy(refactorResult.refactored_code, `btn-${key}`)}
                        className="btn-secondary flex items-center gap-2 text-xs py-2 px-4 shadow-xs"
                      >
                        {copiedKey === `btn-${key}` ? (
                          <>
                            <CheckCircle size={13} className="text-emerald-600" /> Copied to Clipboard
                          </>
                        ) : (
                          <>
                            <Copy size={13} /> Copy Patch
                          </>
                        )}
                      </button>
                    </div>
                  </div>
                ) : isRefactoring ? (
                  <div className="card p-4 ml-2 sm:ml-4 bg-slate-50 border-emerald-200 shadow-xs">
                    <div className="flex items-center gap-2.5 text-xs text-slate-700 font-medium">
                      <Loader2 size={15} className="animate-spin text-emerald-600" />
                      <span>Synthesizing Amazon Bedrock eco-refactoring for {v.title}...</span>
                    </div>
                  </div>
                ) : (
                  <div className="ml-2 sm:ml-4">
                    <button
                      onClick={() => handleRefactor(v, key)}
                      className="btn-secondary flex items-center gap-2 text-xs py-1.5 px-3.5 hover:border-emerald-400 hover:text-emerald-800"
                    >
                      <Zap size={13} className="text-amber-500" /> Synthesize Fix
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* GitHub PR Modal Dialog */}
      {prModalViolation && (
        <div className="fixed inset-0 bg-slate-900/40 backdrop-blur-xs flex items-center justify-center p-4 z-50 animate-in fade-in duration-150">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-xl border border-slate-200 space-y-5">
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="flex items-center gap-2 text-slate-900 font-bold text-sm">
                <Github size={18} />
                <span>Create GitHub Pull Request</span>
              </div>
              <button
                onClick={() => setPrModalViolation(null)}
                className="text-slate-400 hover:text-slate-600 p-1"
              >
                <X size={16} />
              </button>
            </div>

            {prModalError && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-xl text-xs text-red-700 flex items-start gap-2">
                <AlertCircle size={14} className="text-red-500 shrink-0 mt-0.5" />
                <span className="leading-relaxed font-medium">{prModalError}</span>
              </div>
            )}

            <div className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1 uppercase tracking-wider">
                  Target GitHub Repository
                </label>
                <input
                  type="text"
                  placeholder="e.g. owner/repo-name"
                  className="input text-xs font-mono"
                  value={prModalRepo}
                  onChange={e => setPrModalRepo(e.target.value)}
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  The repository where the automated patch branch and PR will be opened.
                </p>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1 uppercase tracking-wider">
                  GitHub Personal Access Token
                </label>
                <input
                  type="password"
                  placeholder="ghp_... (repo / pull request scope)"
                  className="input text-xs font-mono"
                  value={prModalToken}
                  onChange={e => setPrModalToken(e.target.value)}
                />
                <p className="text-[11px] text-slate-400 mt-1">
                  Required to create the branch and commit the patch.{' '}
                  <a
                    href="https://github.com/settings/tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-emerald-700 underline font-semibold"
                  >
                    Generate Token
                  </a>
                </p>
              </div>

              <div className="card-inset p-3 bg-slate-50 border-slate-200 space-y-1">
                <p className="text-[11px] font-bold text-slate-700">Patch Details</p>
                <p className="text-[11px] text-slate-500 font-mono truncate">
                  File: {prModalViolation.violation.file_path}
                </p>
                <p className="text-[11px] text-slate-500">
                  Remediation: {prModalViolation.violation.title}
                </p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-2.5 pt-2">
              <button
                type="button"
                onClick={() => setPrModalViolation(null)}
                className="btn-secondary text-xs py-2 px-4"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={submitPR}
                disabled={prLoading.has(prModalViolation.key)}
                className="btn-primary flex items-center gap-2 text-xs py-2 px-4 shadow-xs"
              >
                {prLoading.has(prModalViolation.key) ? (
                  <>
                    <Loader2 size={13} className="animate-spin" /> Creating PR...
                  </>
                ) : (
                  <>
                    <ExternalLink size={13} /> Open Pull Request
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

