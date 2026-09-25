import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Github, Leaf, Loader2, AlertCircle, Eye, EyeOff, ExternalLink } from 'lucide-react';

const TOKEN_HELP_URL =
  'https://github.com/settings/tokens/new?scopes=repo&description=GreenCode%20Auditor';

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { connectGitHub } = useAuth();

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
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500 to-teal-700 text-white shadow-lg shadow-emerald-500/20 mb-4">
            <Leaf size={26} className="fill-white/20" />
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight text-slate-900">GreenCode Auditor</h1>
          <p className="text-slate-500 mt-1.5 text-sm">
            Connect your GitHub account to audit its repositories
          </p>
        </div>

        <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-7">
          <div className="flex items-center gap-2.5 mb-6">
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
              <Github size={17} />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-900">Sign in with GitHub</h2>
              <p className="text-xs text-slate-500">A personal access token is the only credential used</p>
            </div>
          </div>

          {error && (
            <div
              role="alert"
              className="flex items-start gap-2.5 p-3 mb-5 rounded-lg bg-red-50 border border-red-200"
            >
              <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
              <p className="text-sm text-red-700 leading-relaxed">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label htmlFor="gh-token" className="block text-sm font-semibold text-slate-700 mb-1.5">
                Personal Access Token
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
                  className="input pr-11 font-mono text-sm"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                >
                  {showToken ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
              <a
                href={TOKEN_HELP_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-900 hover:underline mt-2"
              >
                Generate a token with the &quot;repo&quot; scope
                <ExternalLink size={11} />
              </a>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="btn-primary w-full flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  Verifying with GitHub...
                </>
              ) : (
                <>
                  <Github size={16} />
                  Connect GitHub
                </>
              )}
            </button>
          </form>

          <div className="mt-6 pt-5 border-t border-slate-100">
            <p className="text-xs text-slate-500 leading-relaxed">
              Your token is stored encrypted on the server and is never sent back to your
              browser. Revoke it any time from your GitHub token settings.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
