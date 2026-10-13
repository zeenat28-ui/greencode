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
  Lock,
  Code2,
  Cpu,
  Layers,
  ShieldCheck,
  CheckCircle2,
  Globe2,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BrandLogo from '../components/common/BrandLogo';

const ENTERPRISE_FEATURES = [
  {
    icon: Code2,
    title: 'Polyglot AST & Call-Graph Engine',
    description:
      'Static asymptotic complexity, recursion tree depth, and quadratic string/loop pattern detection across Python, TypeScript, Go, Rust, and Java.',
  },
  {
    icon: Cpu,
    title: 'Hardware Energy & RAPL Attribution',
    description:
      'Direct Linux RAPL energy register sampling, cgroup v2 per-PID CPU quota accounting, and calibrated SPECpower hardware curves.',
  },
  {
    icon: Layers,
    title: 'Cloud FinOps FOCUS 1.4 & AWS Integration',
    description:
      'AWS STS AssumeRole session authentication, 19 AWS region grid carbon intensity mapping, and automated GitHub SARIF PR commenting.',
  },
];

export default function Login() {
  const { connectGitHub } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/dashboard';

  const [githubToken, setGithubToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    const trimmed = githubToken.trim();
    if (!trimmed) {
      setError('Please provide a valid GitHub Personal Access Token to continue.');
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

  return (
    <div className="min-h-screen bg-[#0A0D14] text-slate-100 flex flex-col justify-between font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200 relative overflow-hidden">
      {/* Ambient background illumination (Microsoft / AWS / Stripe Enterprise Canvas) */}
      <div
        className="absolute top-0 left-1/4 w-[800px] h-[500px] bg-gradient-to-br from-emerald-500/12 via-teal-500/5 to-transparent blur-[140px] pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute bottom-0 right-1/4 w-[600px] h-[400px] bg-gradient-to-tl from-emerald-600/8 via-cyan-600/4 to-transparent blur-[120px] pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute inset-0 opacity-[0.03] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
          backgroundSize: '48px 48px',
        }}
        aria-hidden="true"
      />

      {/* Top Header */}
      <header className="relative z-10 w-full max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-6 flex items-center justify-between border-b border-white/[0.06]">
        <div className="flex items-center gap-3">
          <BrandLogo size="md" className="ring-1 ring-white/10 shadow-md" />
          <div className="flex flex-col">
            <div className="flex items-center gap-2">
              <span className="font-bold text-base tracking-tight text-white">GreenCode</span>
              <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                v2.1.0 Enterprise
              </span>
            </div>
            <span className="text-[11px] font-mono text-slate-400 hidden sm:inline">
              ISO/IEC 21031:2024 Software Carbon Intensity &amp; FinOps Platform
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="hidden md:flex items-center gap-2 text-xs font-mono text-slate-400 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-white/[0.06]">
            <Globe2 size={13} className="text-emerald-400" />
            <span>19 AWS Regions &middot; Electricity Maps Live</span>
          </div>
          <a
            href="https://github.com/zeenat28-ui/greencode"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-xs font-mono text-slate-300 hover:text-white border border-white/[0.08] transition-colors"
          >
            <Github size={13} />
            <span className="hidden sm:inline">GitHub Repository</span>
            <ExternalLink size={10} className="text-slate-500" />
          </a>
        </div>
      </header>

      {/* Main Full-Width Balanced Hero Section (Fixes Zoom-Out on 1080p/4K Screens) */}
      <main className="relative z-10 flex-1 w-full max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-10 lg:py-16 grid lg:grid-cols-12 gap-12 lg:gap-16 items-center">
        {/* Left Column (7 Columns) — Platform Overview & Enterprise Capabilities */}
        <div className="lg:col-span-7 space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-mono font-medium">
              <ShieldCheck size={13} />
              <span>Enterprise Software Carbon Intensity (GSF SCI)</span>
            </div>
            <h1 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-white leading-[1.15]">
              Automated Code Efficiency &amp; Cloud FinOps Governance
            </h1>
            <p className="text-sm sm:text-base text-slate-300 max-w-2xl leading-relaxed">
              GreenCode statically audits polyglot source code, profiles hardware energy draw via Linux RAPL registers, and reconciles cloud bills with regional grid carbon emissions.
            </p>
          </div>

          {/* 3 Real Architecture Feature Cards */}
          <div className="grid sm:grid-cols-1 gap-3.5 pt-2">
            {ENTERPRISE_FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <div
                  key={feature.title}
                  className="flex items-start gap-4 p-4 rounded-xl bg-slate-900/60 border border-white/[0.06] hover:border-emerald-500/30 transition-all duration-200"
                >
                  <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5">
                    <Icon size={18} />
                  </div>
                  <div className="space-y-1 min-w-0">
                    <h2 className="text-sm font-semibold text-white tracking-tight">
                      {feature.title}
                    </h2>
                    <p className="text-xs text-slate-400 leading-relaxed">
                      {feature.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Standards & Compliance Row */}
          <div className="flex flex-wrap items-center gap-y-2 gap-x-6 pt-2 text-xs font-mono text-slate-400">
            <span className="flex items-center gap-1.5 text-slate-300">
              <CheckCircle2 size={13} className="text-emerald-400" />
              ISO/IEC 21031:2024 (GSF SCI)
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <CheckCircle2 size={13} className="text-emerald-400" />
              FinOps Foundation FOCUS 1.4
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <CheckCircle2 size={13} className="text-emerald-400" />
              OpenTelemetry OTLP / SARIF 2.1.0
            </span>
            <span className="flex items-center gap-1.5 text-slate-300">
              <CheckCircle2 size={13} className="text-emerald-400" />
              Apache-2.0 License
            </span>
          </div>
        </div>

        {/* Right Column (5 Columns) — Substantial Authentication Card */}
        <div className="lg:col-span-5 w-full">
          <div className="bg-[#121622]/90 backdrop-blur-2xl border border-white/[0.1] rounded-2xl p-7 sm:p-9 shadow-2xl shadow-black/80 space-y-6">
            <div className="space-y-2">
              <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-white/[0.06] border border-white/[0.08] text-slate-300 text-[11px] font-mono">
                <Lock size={11} className="text-emerald-400" />
                <span>Developer Authentication</span>
              </div>
              <h2 className="text-2xl font-bold tracking-tight text-white">
                Sign in to Workspace
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed">
                Provide your GitHub Personal Access Token to connect your repositories and run live energy &amp; carbon audits.
              </p>
            </div>

            {error && (
              <div
                role="alert"
                className="flex items-start gap-2.5 p-3.5 rounded-xl bg-rose-950/50 border border-rose-500/30 text-xs text-rose-300 animate-fade-in"
              >
                <AlertCircle size={16} className="text-rose-400 shrink-0 mt-0.5" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4" noValidate>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label
                    htmlFor="github-token"
                    className="block text-xs font-medium text-slate-200"
                  >
                    GitHub Personal Access Token
                  </label>
                  <a
                    href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1 text-[11px] font-mono text-emerald-400 hover:text-emerald-300 transition-colors"
                  >
                    <span>Generate token</span>
                    <ExternalLink size={10} />
                  </a>
                </div>
                <div className="relative">
                  <KeyRound
                    size={15}
                    className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none"
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
                    className="w-full bg-[#090C14] border border-white/[0.1] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-xl pl-10 pr-10 py-3 text-xs font-mono text-white placeholder-slate-600 outline-none transition-all duration-200"
                  />
                  <button
                    type="button"
                    onClick={() => setShowToken((s) => !s)}
                    aria-label={showToken ? 'Hide token' : 'Show token'}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 rounded"
                  >
                    {showToken ? <EyeOff size={15} /> : <Eye size={15} />}
                  </button>
                </div>
                <p className="mt-2 text-[11px] text-slate-400">
                  Required scopes: <code className="font-mono text-slate-200 bg-white/[0.08] px-1.5 py-0.5 rounded">repo</code> and <code className="font-mono text-slate-200 bg-white/[0.08] px-1.5 py-0.5 rounded">read:user</code>.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 px-4 bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 active:from-emerald-700 active:to-emerald-800 text-white font-medium text-xs rounded-xl shadow-lg shadow-emerald-950/50 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 size={15} className="animate-spin text-white" />
                    <span>Verifying token scopes...</span>
                  </>
                ) : (
                  <>
                    <Github size={15} />
                    <span>Continue with GitHub</span>
                    <ArrowRight size={14} className="text-emerald-200" />
                  </>
                )}
              </button>
            </form>

            {/* Ephemeral Session Security Guarantee */}
            <div className="pt-3 border-t border-white/[0.06] flex items-start gap-2.5 text-[11px] text-slate-400 leading-relaxed">
              <Lock size={13} className="text-slate-400 shrink-0 mt-0.5" />
              <span>
                <strong>Ephemeral In-Memory Session:</strong> Token is retained only in browser memory during your active session. It is never persisted to disk, database, or backend server logs.
              </span>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-7xl mx-auto px-6 sm:px-8 lg:px-12 py-5 border-t border-white/[0.06] flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-slate-400 font-mono">
        <div className="flex items-center gap-2">
          <span>&copy; 2026 Zeenat (@zeenat28-ui)</span>
          <span>&middot;</span>
          <span>GreenCode Auditor</span>
        </div>
        <div className="flex items-center gap-4">
          <span>ISO/IEC 21031:2024</span>
          <span>FinOps FOCUS 1.4</span>
          <span>OpenTelemetry OTLP</span>
        </div>
      </footer>
    </div>
  );
}
