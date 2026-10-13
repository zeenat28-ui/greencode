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
    <div className="min-h-screen bg-[#08090E] text-slate-100 flex flex-col justify-between font-sans antialiased selection:bg-emerald-500/30 selection:text-emerald-200 relative overflow-hidden">
      {/* Background Ambient Glow (Linear / Supabase Style) */}
      <div 
        className="absolute top-0 left-1/2 -translate-x-1/2 w-[700px] h-[400px] bg-gradient-to-b from-emerald-500/15 via-emerald-600/5 to-transparent blur-[140px] pointer-events-none"
        aria-hidden="true"
      />
      <div
        className="absolute inset-0 opacity-[0.02] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(to right, #ffffff 1px, transparent 1px), linear-gradient(to bottom, #ffffff 1px, transparent 1px)',
          backgroundSize: '36px 36px',
        }}
        aria-hidden="true"
      />

      {/* Top Header */}
      <header className="relative z-10 w-full max-w-5xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <BrandLogo size="sm" className="ring-1 ring-white/10 shadow-sm" />
          <span className="font-semibold text-sm tracking-tight text-white">
            GreenCode
          </span>
          <span className="text-[10px] font-mono text-emerald-400 bg-emerald-950/60 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            v2.1.0
          </span>
        </div>
        <a
          href="https://github.com/zeenat28-ui/greencode"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs font-mono text-slate-400 hover:text-white transition-colors"
        >
          <Github size={13} />
          <span>GitHub</span>
          <ExternalLink size={10} className="text-slate-500" />
        </a>
      </header>

      {/* Main Container */}
      <main className="w-full max-w-[420px] mx-auto px-4 my-auto relative z-10 py-8">
        {/* Logo & Header Section */}
        <div className="flex flex-col items-center text-center mb-7">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-tr from-emerald-500/20 via-zinc-800 to-white/10 p-[1px] shadow-lg shadow-emerald-950/30 mb-4">
            <div className="w-full h-full bg-[#0D0F17] rounded-[15px] flex items-center justify-center">
              <BrandLogo size="md" />
            </div>
          </div>
          <h1 className="text-xl font-semibold tracking-tight text-white">
            Sign in to GreenCode
          </h1>
          <p className="text-xs text-slate-400 mt-1.5 max-w-xs leading-relaxed">
            Enter your GitHub Personal Access Token to audit repository carbon intensity and cloud FinOps spend.
          </p>
        </div>

        {/* Card Box */}
        <div className="bg-[#12131A]/90 backdrop-blur-xl border border-white/[0.08] rounded-2xl p-7 shadow-2xl shadow-black/70 space-y-5">
          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 rounded-xl bg-rose-950/40 border border-rose-500/30 text-xs text-rose-300 animate-fade-in"
            >
              <AlertCircle size={15} className="text-rose-400 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="github-token"
                  className="block text-xs font-medium text-slate-300"
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
                  size={14}
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
                  className="w-full bg-[#08090E] border border-white/[0.08] focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 rounded-xl pl-9 pr-9 py-2.5 text-xs font-mono text-white placeholder-slate-600 outline-none transition-all duration-200"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 p-1 rounded"
                >
                  {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-400">
                Requires <code className="font-mono text-slate-300 bg-white/[0.06] px-1 py-0.5 rounded">repo</code> and <code className="font-mono text-slate-300 bg-white/[0.06] px-1 py-0.5 rounded">read:user</code> scopes.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 bg-gradient-to-b from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 active:from-emerald-700 active:to-emerald-800 text-white font-medium text-xs rounded-xl shadow-lg shadow-emerald-950/40 transition-all duration-200 flex items-center justify-center gap-2 disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 size={14} className="animate-spin text-white" />
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <Github size={14} />
                  <span>Continue with GitHub</span>
                  <ArrowRight size={13} className="text-emerald-200" />
                </>
              )}
            </button>
          </form>

          {/* Ephemeral Session Security Guarantee */}
          <div className="pt-3 border-t border-white/[0.06] flex items-start gap-2 text-[11px] text-slate-400 leading-relaxed">
            <Lock size={12} className="text-slate-400 shrink-0 mt-0.5" />
            <span>
              <strong>Ephemeral Session:</strong> Token is retained solely in client memory during the active session. It is never saved to disk, database, or server logs.
            </span>
          </div>
        </div>

        {/* Specifications row */}
        <div className="flex items-center justify-center gap-3 text-xs text-slate-400 font-mono mt-6">
          <span>ISO/IEC 21031:2024</span>
          <span>&middot;</span>
          <span>FinOps FOCUS 1.4</span>
          <span>&middot;</span>
          <span>Apache-2.0</span>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10 w-full max-w-5xl mx-auto px-6 py-4 text-center text-xs text-slate-400 font-mono">
        <span>&copy; 2026 Zeenat (@zeenat28-ui) &middot; GreenCode Platform</span>
      </footer>
    </div>
  );
}
