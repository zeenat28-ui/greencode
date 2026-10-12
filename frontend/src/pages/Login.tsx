import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Github,
  KeyRound,
  ArrowRight,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
  ExternalLink,
  Terminal,
  Cpu,
  Activity,
  GitPullRequest,
  CheckCircle2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BrandLogo from '../components/common/BrandLogo';

const CAPABILITY_HIGHLIGHTS = [
  {
    icon: Terminal,
    title: 'Polyglot AST & Call-Graph',
    detail: 'Cross-function loop depth and complexity analysis across Python, TypeScript, Go, Rust, and Java.',
  },
  {
    icon: Cpu,
    title: 'Hardware & Grid Telemetry',
    detail: 'Linux RAPL, cgroup v2 per-PID energy attribution, SPECpower curves, and live marginal grid intensity.',
  },
  {
    icon: GitPullRequest,
    title: 'CI/CD Gates & FinOps FOCUS 1.4',
    detail: 'GitHub SARIF 2.1.0 code scanning, automated PR diff remediation, and OpenTelemetry OTLP export.',
  },
];

export default function Login() {
  const { connectGitHub, loginAsDemo } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/dashboard';

  const [githubToken, setGithubToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [loading, setLoading] = useState(false);
  const [guestLoading, setGuestLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trimmed = githubToken.trim();
    if (!trimmed) {
      setError('Enter a valid GitHub Personal Access Token to continue.');
      return;
    }
    setLoading(true);
    try {
      await connectGitHub(trimmed);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const eObj = err as { response?: { data?: { detail?: string } }; message?: string };
      const detail =
        eObj?.response?.data?.detail ||
        eObj?.message ||
        'Authentication failed. Verify your token scopes and try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  const handleWorkspacePreview = () => {
    setError(null);
    setGuestLoading(true);
    try {
      loginAsDemo();
    } finally {
      setGuestLoading(false);
    }
  };

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-white text-zinc-900">
      {/* Left Column — Clean Developer Sign-In */}
      <div className="flex flex-col justify-between px-6 py-8 sm:px-12 lg:px-16 xl:px-24 bg-white border-r border-zinc-200/80">
        {/* Top Bar */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <BrandLogo size="sm" />
            <span className="font-semibold text-[15px] tracking-tight text-zinc-950">
              GreenCode
            </span>
            <span className="text-[11px] font-mono font-medium px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-600 border border-zinc-200/80">
              v2.1.0
            </span>
          </div>
          <a
            href="https://github.com/zeenat28-ui/greencode"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-zinc-500 hover:text-zinc-900 transition-colors"
          >
            <Github size={14} />
            <span>GitHub</span>
            <ExternalLink size={11} />
          </a>
        </div>

        {/* Center Sign-In Workspace */}
        <div className="w-full max-w-[380px] mx-auto my-12">
          <div className="mb-7">
            <h1 className="text-2xl font-semibold text-zinc-950 tracking-tight">
              Sign in to GreenCode
            </h1>
            <p className="text-sm text-zinc-500 mt-1.5 leading-relaxed">
              Authenticate with a GitHub personal access token to audit repositories, or open the interactive workspace.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="mb-5 flex items-start gap-2.5 p-3 rounded-lg bg-red-50/80 border border-red-200 text-xs text-red-700"
            >
              <AlertCircle size={15} className="text-red-600 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="github-token"
                  className="block text-xs font-medium text-zinc-700"
                >
                  GitHub Personal Access Token
                </label>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800 transition-colors"
                >
                  <span>Create token</span>
                  <ExternalLink size={11} />
                </a>
              </div>
              <div className="relative">
                <KeyRound
                  size={15}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
                />
                <input
                  id="github-token"
                  type={showToken ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  required
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="w-full pl-9 pr-9 py-2.5 text-xs font-mono bg-white border border-zinc-200 rounded-lg text-zinc-900 placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-zinc-400 hover:text-zinc-700 p-1 rounded"
                >
                  {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="mt-1.5 text-[11px] text-zinc-500">
                Requires <code className="font-mono text-zinc-700 bg-zinc-100 px-1 py-0.5 rounded">repo</code> and <code className="font-mono text-zinc-700 bg-zinc-100 px-1 py-0.5 rounded">read:user</code> scopes for repository analysis.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading || guestLoading}
              className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white text-xs font-medium flex items-center justify-center gap-2 transition-colors shadow-xs disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <Github size={14} />
                  <span>Continue with GitHub</span>
                  <ArrowRight size={13} />
                </>
              )}
            </button>
          </form>

          <div className="relative my-6">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t border-zinc-200" />
            </div>
            <div className="relative flex justify-center text-[11px]">
              <span className="bg-white px-2.5 text-zinc-400 font-medium">
                or
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={handleWorkspacePreview}
            disabled={loading || guestLoading}
            className="w-full py-2.5 px-4 rounded-lg bg-white hover:bg-zinc-50 text-zinc-800 border border-zinc-200 hover:border-zinc-300 text-xs font-medium flex items-center justify-center gap-2 transition-all shadow-2xs disabled:opacity-50"
          >
            {guestLoading ? (
              <>
                <Loader2 size={14} className="animate-spin text-emerald-600" />
                <span>Initializing workspace...</span>
              </>
            ) : (
              <>
                <Activity size={14} className="text-emerald-600" />
                <span>Open Interactive Workspace</span>
              </>
            )}
          </button>
          <p className="text-[11px] text-zinc-400 text-center mt-2">
            Explore pre-loaded repository audits, SCI metrics, and FinOps cost models without a token.
          </p>
        </div>

        {/* Bottom Metadata Footer */}
        <div className="flex flex-wrap items-center justify-between gap-2 text-[11px] text-zinc-400 pt-4 border-t border-zinc-100">
          <span>Apache-2.0 Open Source</span>
          <span>&middot;</span>
          <span>ISO/IEC 21031:2024 (GSF SCI)</span>
          <span>&middot;</span>
          <span>Local-first AST Engine</span>
        </div>
      </div>

      {/* Right Column — Dark Engineering Telemetry Showcase */}
      <div className="hidden lg:flex flex-col justify-between p-12 xl:p-16 bg-[#090D16] text-zinc-100 relative overflow-hidden select-none">
        {/* Subtle grid background + radial emerald glow */}
        <div
          className="absolute inset-0 opacity-20 pointer-events-none"
          style={{
            backgroundImage:
              'linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)',
            backgroundSize: '32px 32px',
          }}
        />
        <div
          className="absolute -top-32 -right-32 w-96 h-96 rounded-full pointer-events-none blur-3xl opacity-20"
          style={{
            background: 'radial-gradient(circle, #10b981 0%, transparent 70%)',
          }}
        />

        {/* Top Spec Bar */}
        <div className="relative z-10 flex items-center justify-between">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-zinc-900/90 border border-zinc-800 text-[11px] font-mono text-zinc-300">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            <span>GSF SCI v1.0 &middot; FOCUS 1.4 &middot; OTLP/HTTP v1</span>
          </div>
          <span className="text-xs font-mono text-zinc-500">
            Zero-Telemetry Static &amp; Dynamic Profiler
          </span>
        </div>

        {/* Center Terminal & Live Telemetry Preview */}
        <div className="relative z-10 my-auto space-y-6">
          <div className="rounded-xl bg-[#0D1117] border border-zinc-800/90 shadow-2xl overflow-hidden">
            {/* Terminal Titlebar */}
            <div className="px-4 py-2.5 bg-zinc-900/80 border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
                <span className="w-2.5 h-2.5 rounded-full bg-zinc-700" />
              </div>
              <span className="text-[11px] font-mono text-zinc-400">
                greencode-cli &mdash; audit pipeline
              </span>
              <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-800/50 px-1.5 py-0.5 rounded">
                PASS
              </span>
            </div>

            {/* Terminal Output */}
            <div className="p-5 font-mono text-xs space-y-2.5 leading-relaxed">
              <div className="text-zinc-300">
                <span className="text-emerald-400">$</span> greencode --path ./app --diff origin/main...HEAD --sarif audit.sarif
              </div>
              <div className="text-zinc-500">
                [1/4] Building polyglot AST &amp; cross-function call graph (74 modules)...
              </div>
              <div className="text-zinc-500">
                [2/4] Sampling Linux RAPL &amp; cgroup v2 per-PID energy counters...
              </div>
              <div className="text-zinc-500">
                [3/4] Computing ISO/IEC 21031:2024 SCI &amp; FinOps FOCUS 1.4 attribution...
              </div>
              <div className="pt-2 border-t border-zinc-800/80 grid grid-cols-3 gap-3">
                <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800/80">
                  <div className="text-[10px] text-zinc-500 uppercase">Green Score</div>
                  <div className="text-sm font-semibold text-emerald-400 mt-0.5">100.0 / 100</div>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800/80">
                  <div className="text-[10px] text-zinc-500 uppercase">SCI Intensity</div>
                  <div className="text-sm font-semibold text-zinc-100 mt-0.5">0.014 gCO₂e</div>
                </div>
                <div className="p-2.5 rounded-lg bg-zinc-900/70 border border-zinc-800/80">
                  <div className="text-[10px] text-zinc-500 uppercase">Scan Latency</div>
                  <div className="text-sm font-semibold text-zinc-100 mt-0.5">0.14 ms/file</div>
                </div>
              </div>
              <div className="pt-1 flex items-center gap-2 text-emerald-400 text-[11px]">
                <CheckCircle2 size={13} />
                <span>SARIF 2.1.0 report &amp; OTLP metrics exported (0 violations).</span>
              </div>
            </div>
          </div>

          {/* 3 Engineering Capability Cards */}
          <div className="grid grid-cols-1 gap-3">
            {CAPABILITY_HIGHLIGHTS.map((item) => {
              const IconComponent = item.icon;
              return (
                <div
                  key={item.title}
                  className="p-3.5 rounded-xl bg-zinc-900/50 border border-zinc-800/80 flex items-start gap-3"
                >
                  <div className="p-2 rounded-lg bg-zinc-800/80 text-emerald-400 shrink-0 mt-0.5">
                    <IconComponent size={15} />
                  </div>
                  <div>
                    <div className="text-xs font-semibold text-zinc-100">
                      {item.title}
                    </div>
                    <p className="text-xs text-zinc-400 mt-0.5 leading-relaxed">
                      {item.detail}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Bottom Architecture Caption */}
        <div className="relative z-10 flex items-center justify-between text-xs text-zinc-500 font-mono">
          <span>Python &middot; TypeScript &middot; Go &middot; Rust &middot; Java</span>
          <span>Docker &middot; GitHub Actions &middot; MCP Server</span>
        </div>
      </div>
    </div>
  );
}
