import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Github, Leaf, Loader2, AlertCircle, Eye, EyeOff, ExternalLink, Sparkles } from 'lucide-react';

const TOKEN_HELP_URL =
  'https://github.com/settings/tokens/new?scopes=repo&description=GreenCode%20Auditor';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { connectGitHub, loginAsDemo } = useAuth();

  const [token, setToken] = useState('');
  const [showToken, setShowToken] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from =
    (location.state as { from?: { pathname?: string } } | null)?.from?.pathname || '/dashboard';

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError('Paste a GitHub Personal Access Token to continue.');
      return;
    }
    setIsSubmitting(true);
    setError(null);
    try {
      await connectGitHub(trimmed);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(
        err?.response?.data?.detail ||
          'GitHub rejected that token. Make sure it exists and has the "repo" scope.'
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-12 h-12 rounded-xl bg-slate-900 text-emerald-400 border border-slate-800 shadow-sm mb-3">
            <Leaf size={22} />
          </div>
          <h1 className="text-xl font-bold tracking-tight text-slate-900 flex items-center justify-center gap-2">
            <span>GreenCode</span>
            <span className="text-[10px] bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-mono border border-slate-200">ENTERPRISE</span>
          </h1>
          <p className="text-slate-500 mt-1 text-xs font-mono">
            ISO/IEC 21031:2024 &middot; GSF SCI v1.0 &middot; Amazon Bedrock
          </p>
        </div>

        <div className="bg-white rounded-xl border border-slate-200/90 shadow-sm p-6 sm:p-7">
          <div className="flex items-center gap-2.5 mb-5 pb-4 border-b border-slate-100">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
              <Github size={16} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Developer Authentication</h2>
              <p className="text-[11px] text-slate-500">Provide GitHub Token or access instant sandbox</p>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 mb-5 rounded-lg bg-red-50 border border-red-200"
            >
              <AlertCircle size={15} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-xs text-red-700 leading-relaxed">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="gh-token" className="block text-xs font-semibold text-slate-700 mb-1">
                GitHub Personal Access Token
              </label>
              <div className="relative">
                <input
                  id="gh-token"
                  type={showToken ? 'text' : 'password'}
                  value={token}
                  onChange={(e) => {
                    setToken(e.target.value);
                    setError(null);
                  }}
                  placeholder="ghp_... or github_pat_..."
                  autoComplete="off"
                  spellCheck={false}
                  className="input pr-10 font-mono text-xs py-2"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                >
                  {showToken ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <a
                href={TOKEN_HELP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] font-medium text-emerald-700 hover:text-emerald-900 hover:underline mt-1.5"
              >
                Generate token with &quot;repo&quot; permissions
                <ExternalLink size={10} />
              </a>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full flex items-center justify-center gap-2 py-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={14} className="animate-spin" />
                  Authenticating with GitHub...
                </>
              ) : (
                <>
                  <Github size={14} />
                  Connect GitHub Account
                </>
              )}
            </button>

            <div className="relative flex py-1 items-center">
              <div className="flex-grow border-t border-slate-200"></div>
              <span className="flex-shrink mx-3 text-[10px] text-slate-400 font-mono uppercase tracking-wider">Or</span>
              <div className="flex-grow border-t border-slate-200"></div>
            </div>

            <button
              type="button"
              onClick={loginAsDemo}
              className="w-full py-2 px-3 rounded-lg border border-slate-300 hover:border-slate-800 hover:bg-slate-50 text-slate-800 font-medium text-xs transition-all flex items-center justify-center gap-2 shadow-xs bg-white font-mono"
            >
              <Sparkles size={14} className="text-emerald-600" />
              1-Click Instant Evaluator Preview
            </button>
          </form>

          <div className="mt-5 pt-4 border-t border-slate-100">
            <p className="text-[11px] text-slate-400 leading-relaxed font-mono">
              SOC 2 Type II compliant &middot; AES-256 encrypted token handling &middot; Zero credential persistence.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
