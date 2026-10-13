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
  ShieldCheck,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BrandLogo from '../components/common/BrandLogo';

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
    <div className="min-h-screen flex flex-col justify-between bg-[#FAFAFA] text-zinc-900 px-4 py-8 sm:py-12 selection:bg-emerald-100 selection:text-emerald-900">
      {/* Top Header Bar */}
      <header className="w-full max-w-5xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BrandLogo size="sm" />
          <span className="font-semibold text-base tracking-tight text-zinc-950">
            GreenCode
          </span>
          <span className="text-[11px] font-mono text-zinc-500 bg-zinc-100 border border-zinc-200/80 px-2 py-0.5 rounded-md">
            v2.1.0
          </span>
        </div>
        <a
          href="https://github.com/zeenat28-ui/greencode"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-zinc-600 hover:text-zinc-950 transition-colors"
        >
          <Github size={13} />
          <span>Source</span>
          <ExternalLink size={10} className="text-zinc-400" />
        </a>
      </header>

      {/* Main Authentication Card */}
      <main className="w-full max-w-md mx-auto my-auto py-8">
        <div className="card-elevated p-8 sm:p-9 space-y-6 bg-white border border-zinc-200/90 shadow-xl shadow-zinc-950/[0.04]">
          {/* Card Header */}
          <div className="text-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-zinc-50 border border-zinc-200/80 flex items-center justify-center mx-auto shadow-xs">
              <BrandLogo size="md" />
            </div>
            <h1 className="text-xl font-semibold text-zinc-950 tracking-tight pt-1">
              Sign in to GreenCode
            </h1>
            <p className="text-xs text-zinc-500 max-w-xs mx-auto leading-relaxed">
              Authenticate with your GitHub Personal Access Token to audit repository carbon intensity and FinOps spend.
            </p>
          </div>

          {/* Error Message */}
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 animate-fade-in"
            >
              <AlertCircle size={15} className="text-rose-600 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {/* Form */}
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
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 hover:text-emerald-800 transition-colors"
                >
                  <span>Create token</span>
                  <ExternalLink size={10} />
                </a>
              </div>
              <div className="relative">
                <KeyRound
                  size={14}
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
                Requires <code className="font-mono text-zinc-700 bg-zinc-100 px-1 py-0.5 rounded">repo</code> and <code className="font-mono text-zinc-700 bg-zinc-100 px-1 py-0.5 rounded">read:user</code> scopes to analyze repositories.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-zinc-900 hover:bg-zinc-800 active:bg-zinc-950 text-white text-xs font-medium flex items-center justify-center gap-2 transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
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

          {/* Security & In-Memory Guarantee */}
          <div className="pt-3 border-t border-zinc-100 flex items-start gap-2 text-[11px] text-zinc-500 leading-relaxed">
            <Lock size={12} className="text-zinc-400 shrink-0 mt-0.5" />
            <span>
              <strong>Ephemeral Session:</strong> Token is retained only in client memory during your active browser tab and is never persisted to disk or backend database.
            </span>
          </div>
        </div>

        {/* Specification & Architecture Badges */}
        <div className="mt-6 flex flex-wrap items-center justify-center gap-x-4 gap-y-1 text-xs text-zinc-400 font-mono">
          <span>ISO/IEC 21031:2024 (GSF SCI)</span>
          <span>&middot;</span>
          <span>FinOps FOCUS 1.4</span>
          <span>&middot;</span>
          <span>Apache-2.0</span>
        </div>
      </main>

      {/* Footer */}
      <footer className="w-full max-w-5xl mx-auto text-center text-xs text-zinc-400 font-mono py-2">
        <span>&copy; 2026 Zeenat (@zeenat28-ui) &middot; GreenCode Auditor</span>
      </footer>
    </div>
  );
}
