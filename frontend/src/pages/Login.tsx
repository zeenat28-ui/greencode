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

/**
 * Enterprise Login Screen
 * - Viewport-locked: no scroll, no zoom, no pinch
 * - Centered card with fixed max-width
 * - Works on all laptop/desktop screens without layout shift
 */
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
      setError('Please enter a valid GitHub Personal Access Token to continue.');
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
    <div
      className="font-sans"
      style={{
        /* Hard-lock to the exact viewport — no scroll, no overflow, no bounce */
        position: 'fixed',
        inset: 0,
        width: '100vw',
        height: '100dvh',
        overflow: 'hidden',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: '#fafafa',
        /* Prevent ALL touch gestures (pinch, pan, double-tap) */
        touchAction: 'none',
        WebkitUserSelect: 'none',
        userSelect: 'none',
      }}
    >
      {/* Subtle background gradient matching the brand */}
      <div
        className="pointer-events-none"
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: [
            'radial-gradient(1200px 600px at 100% -10%, rgba(5, 150, 105, 0.05), transparent 60%)',
            'radial-gradient(900px 500px at -10% 110%, rgba(5, 150, 105, 0.04), transparent 55%)',
            'linear-gradient(180deg, #fbfbfb 0%, #f6f7f6 100%)',
          ].join(', '),
        }}
      />

      {/* Centered Column — locked, no vertical drift */}
      <div
        className="relative z-10"
        style={{
          width: '100%',
          maxWidth: '420px',
          padding: '0 24px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          /* Allow text selection inside inputs */
          userSelect: 'text',
          WebkitUserSelect: 'text',
        }}
      >
        {/* ─── Brand Header ─── */}
        <div className="mb-6 flex flex-col items-center text-center select-none">
          <div className="w-12 h-12 rounded-xl bg-white border border-slate-200/90 shadow-sm flex items-center justify-center mb-3">
            <BrandLogo size="md" />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-xl font-bold tracking-tight text-slate-900">GreenCode</span>
            <span className="text-[10px] font-mono font-medium text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">
              v2.1.0
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-1 max-w-xs leading-relaxed">
            Software Carbon Intensity &amp; Cloud FinOps Engine
          </p>
        </div>

        {/* ─── Login Card ─── */}
        <div className="w-full bg-white rounded-2xl border border-slate-200/90 shadow-xl shadow-slate-900/[0.04] p-7 sm:p-8 space-y-5">
          <div>
            <h1 className="text-lg font-semibold text-slate-900 tracking-tight">
              Sign in to your account
            </h1>
            <p className="text-xs text-slate-500 mt-1 leading-relaxed">
              Authenticate with your GitHub Personal Access Token to audit repositories.
            </p>
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700 animate-fade-in"
            >
              <AlertCircle size={15} className="text-rose-600 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label
                  htmlFor="github-token"
                  className="block text-xs font-medium text-slate-700"
                >
                  GitHub Personal Access Token
                </label>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-600 hover:text-emerald-700 transition-colors"
                >
                  <span>Create token</span>
                  <ExternalLink size={10} />
                </a>
              </div>
              <div className="relative">
                <KeyRound
                  size={14}
                  className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
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
                  style={{ touchAction: 'auto' }}
                  className="w-full pl-9 pr-9 py-2.5 text-xs font-mono bg-white border border-slate-200 rounded-lg text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition-all"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                  className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 p-1 rounded transition-colors"
                >
                  {showToken ? <EyeOff size={14} /> : <Eye size={14} />}
                </button>
              </div>
              <p className="mt-1.5 text-[11px] text-slate-500">
                Requires <code className="font-mono text-slate-700 bg-slate-100 px-1 py-0.5 rounded">repo</code> and <code className="font-mono text-slate-700 bg-slate-100 px-1 py-0.5 rounded">read:user</code> scopes to analyze code.
              </p>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 px-4 rounded-lg bg-slate-900 hover:bg-slate-800 active:bg-slate-950 text-white text-xs font-medium flex items-center justify-center gap-2 transition-colors shadow-xs disabled:opacity-50 cursor-pointer"
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

          {/* Ephemeral Session Note */}
          <div className="pt-3 border-t border-slate-100 flex items-start gap-2 text-[11px] text-slate-500 leading-relaxed">
            <Lock size={12} className="text-slate-400 shrink-0 mt-0.5" />
            <span>
              <strong>Ephemeral Session:</strong> Token is retained only in browser memory and is never saved to disk, database, or server logs.
            </span>
          </div>
        </div>

        {/* ─── Footer ─── */}
        <div className="mt-6 flex flex-col items-center gap-2 text-xs text-slate-400 font-mono select-none">
          <div className="flex items-center gap-3 flex-wrap justify-center">
            <span>ISO/IEC 21031:2024</span>
            <span>&middot;</span>
            <span>FinOps FOCUS 1.4</span>
            <span>&middot;</span>
            <span>Apache-2.0</span>
          </div>
          <div className="flex items-center gap-2 flex-wrap justify-center">
            <a
              href="https://github.com/zeenat28-ui/greencode"
              target="_blank"
              rel="noopener noreferrer"
              className="hover:text-slate-600 transition-colors inline-flex items-center gap-1"
            >
              <Github size={11} />
              <span>Source Repository</span>
            </a>
            <span>&middot;</span>
            <span>&copy; 2026 Zeenat (@zeenat28-ui)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
