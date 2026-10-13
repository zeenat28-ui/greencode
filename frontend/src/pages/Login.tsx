import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

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
        'Authentication failed. Please verify your token scopes and try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    // Fixed inset-0 z-50 forces 100% viewport breakout, completely bypassing any parent layout wrappers
    <div className="fixed inset-0 z-50 flex w-screen h-screen min-h-screen bg-gray-50 m-0 p-0 overflow-x-hidden overflow-y-auto lg:overflow-hidden">
      
      {/* Left Section: Branding & Value Proposition (50% Width) */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-900 text-white p-12 flex-col justify-between relative overflow-hidden h-full">
        {/* Abstract Background Accent */}
        <div className="absolute top-0 left-0 w-full h-full opacity-10 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-green-400 via-transparent to-transparent pointer-events-none"></div>
        
        <div className="relative z-10">
          <div className="flex items-center gap-3 mb-12">
            <div className="bg-green-500 p-2 rounded-lg flex items-center justify-center shadow-md">
              <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
              </svg>
            </div>
            <span className="text-2xl font-bold tracking-tight">
              GreenCode <span className="text-green-400 text-sm font-medium ml-1">v2.1.0</span>
            </span>
          </div>
          
          <h1 className="text-4xl font-bold leading-tight mb-6 tracking-tight">
            Software Carbon Intensity &amp;<br />Cloud FinOps Engine
          </h1>
          <p className="text-slate-400 text-lg max-w-md mb-8 leading-relaxed">
            Production Network · All Systems Operational. Authenticate to audit repositories and monitor cloud workloads with high-performance telemetry.
          </p>

          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-3 text-slate-300">
              <svg className="w-5 h-5 text-green-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
              </svg>
              <span>ISO/IEC 21031:2024 Verified</span>
            </div>
            <div className="flex items-center gap-3 text-slate-300">
              <svg className="w-5 h-5 text-green-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd"></path>
              </svg>
              <span>FinOps Foundation FOCUS 1.4</span>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-sm text-slate-500 flex flex-wrap gap-6">
          <a href="https://github.com/zeenat28-ui/greencode" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
            GitHub Repository
          </a>
          <a href="https://github.com/zeenat28-ui/greencode/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="hover:text-white transition-colors">
            Apache-2.0 License
          </a>
          <span>&copy; 2026 Zeenat (@zeenat28-ui)</span>
        </div>
      </div>

      {/* Right Section: Login Form (50% Width) */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-8 sm:p-12 overflow-y-auto h-full">
        <div className="w-full max-w-md">
          
          {/* Mobile Logo */}
          <div className="flex lg:hidden items-center gap-2 mb-8">
            <div className="bg-green-500 p-2 rounded-lg flex items-center justify-center">
              <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"></path>
              </svg>
            </div>
            <span className="text-xl font-bold">GreenCode</span>
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-2 tracking-tight">Sign in to your account</h2>
          <p className="text-gray-500 mb-8">Authenticate with your GitHub Personal Access Token.</p>

          {error && (
            <div className="mb-6 rounded-lg bg-red-50 border border-red-200 p-3.5 text-sm text-red-700 flex items-start gap-2.5" role="alert">
              <svg className="w-5 h-5 text-red-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6" noValidate>
            <div>
              <div className="flex justify-between items-center mb-2">
                <label htmlFor="token" className="block text-sm font-medium text-gray-700">GitHub Personal Access Token</label>
                <a 
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-sm font-medium text-green-600 hover:text-green-500 transition-colors"
                >
                  Create token &rarr;
                </a>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
                  <svg className="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
                  </svg>
                </div>
                <input 
                  type={showToken ? 'text' : 'password'} 
                  id="token" 
                  name="token" 
                  autoComplete="off"
                  spellCheck={false}
                  required 
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" 
                  className="block w-full pl-10 pr-10 py-3 border border-gray-300 rounded-lg focus:ring-green-500 focus:border-green-500 sm:text-sm transition-shadow font-mono" 
                />
                <button
                  type="button"
                  onClick={() => setShowToken(!showToken)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600 focus:outline-none cursor-pointer"
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                >
                  {showToken ? (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                    </svg>
                  ) : (
                    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                    </svg>
                  )}
                </button>
              </div>
              <p className="mt-2 text-xs text-gray-500">
                Required scopes: <span className="font-mono bg-gray-100 px-1 py-0.5 rounded text-gray-700">repo</span> <span className="font-mono bg-gray-100 px-1 py-0.5 rounded text-gray-700">read:user</span>
              </p>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-gray-900 hover:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-900 transition-colors disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                  </svg>
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path fillRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" clipRule="evenodd"></path>
                  </svg>
                  <span>Continue with GitHub</span>
                </>
              )}
            </button>
          </form>

          {/* Security Notice Box */}
          <div className="mt-8 rounded-lg bg-blue-50 border border-blue-100 p-4 flex gap-3">
            <svg className="h-5 w-5 text-blue-500 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
            </svg>
            <div>
              <h3 className="text-sm font-semibold text-blue-900">Client-Side Ephemeral Session</h3>
              <p className="text-xs text-blue-800 mt-1 leading-relaxed">
                Your token is held exclusively in volatile browser memory for API calls. It is never stored on disk, written to local storage, logged to backend servers, or retained across browser closes.
              </p>
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
