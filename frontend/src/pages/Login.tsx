import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, Loader2, AlertCircle, Check, Github, Leaf } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ssoService } from '../services/greencodeApi';

export default function Login() {
  const { connectGitHub } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/dashboard';

  const [email, setEmail] = useState('');
  const [passwordOrToken, setPasswordOrToken] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const performLogin = async (tokenCandidate: string) => {
    const trimmed = tokenCandidate.trim();
    if (!trimmed) {
      setError('Please enter your GitHub Personal Access Token or credentials to sign in.');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await connectGitHub(trimmed);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const eObj = err as { response?: { data?: { detail?: string } }; message?: string };
      const detail =
        eObj?.response?.data?.detail ||
        eObj?.message ||
        'Authentication failed. Please verify your token or credentials.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const token = passwordOrToken || email;
    performLogin(token);
  };

  const handleGitHubQuick = () => {
    if (passwordOrToken.trim()) {
      performLogin(passwordOrToken);
    } else {
      setError('Please paste your GitHub Personal Access Token into the password field below to continue.');
    }
  };

  const handleGoogleQuick = () => {
    setError('Google OAuth is managed via Single Sign-On (SSO) for your corporate domain.');
  };

  const handleSSO = async () => {
    setError(null);
    try {
      const res = await ssoService.initiate();
      if (res.data.sso_enabled && res.data.redirect_url) {
        window.location.href = res.data.redirect_url;
      } else {
        setError('Corporate SSO is available on Enterprise custom domains.');
      }
    } catch {
      setError('Unable to initiate SSO at this time.');
    }
  };

  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden flex flex-col lg:flex-row bg-[#fbfcfa] font-sans text-slate-900 select-none">
      
      {/* ════════════════════════ LEFT HERO PANE (Mint Green #ebf6ee) ════════════════════════ */}
      <div className="lg:w-1/2 bg-[#ebf6ee] px-8 sm:px-12 xl:px-16 py-6 sm:py-8 lg:py-10 flex flex-col justify-between relative overflow-hidden border-b lg:border-b-0 lg:border-r border-[#d8ecdd] h-full">
        
        {/* Subtle Geometric Wireframe Leaf + Cloud Line Art Overlay */}
        <div className="absolute right-0 top-10 lg:top-16 w-72 h-72 pointer-events-none select-none opacity-35 text-[#4c8464]">
          <svg viewBox="0 0 240 240" fill="none" stroke="currentColor" strokeWidth="1.2" className="w-full h-full">
            <path d="M125 75 A 28 28 0 0 1 175 75 A 24 24 0 0 1 205 100 A 24 24 0 0 1 185 140 L 115 140" strokeWidth="1.1" />
            <path d="M145 105 A 32 32 0 0 1 205 105 A 28 28 0 0 1 235 135 L 145 135" strokeWidth="1.1" opacity="0.6" />
            <path d="M150 35 C 205 80, 205 165, 150 205 C 95 165, 95 80, 150 35 Z" strokeWidth="1.5" />
            <path d="M150 35 L 150 205" strokeWidth="1.2" />
            <path d="M150 68 L 178 90 M 150 68 L 122 90" />
            <path d="M150 102 L 188 124 M 150 102 L 112 124" />
            <path d="M150 138 L 182 160 M 150 138 L 118 160" />
            <path d="M150 172 L 166 186 M 150 172 L 134 186" />
          </svg>
        </div>

        {/* Top: Brand Logo & Title (Moved strictly to the top) */}
        <div className="relative z-10 pt-1">
          <div className="flex items-center gap-2.5 mb-6 sm:mb-8 lg:mb-10">
            <div className="w-8 h-8 rounded-lg bg-[#0e482f] flex items-center justify-center text-white font-mono font-bold text-sm shadow-xs">
              <span className="text-emerald-400 text-xs font-semibold mr-0.5">{`{`}</span>
              <Leaf size={14} className="text-emerald-300 stroke-[2.5]" />
              <span className="text-emerald-400 text-xs font-semibold ml-0.5">{`}`}</span>
            </div>
            <span className="text-xl font-bold tracking-tight text-[#0a291c]">
              GreenCode
            </span>
          </div>

          {/* Headline & Clear Value-Driven Body Text */}
          <div className="max-w-[460px]">
            <h1 className="text-3xl sm:text-4xl lg:text-[42px] font-black text-[#0a291c] tracking-tight leading-[1.12] mb-4">
              Build greener,<br />run leaner.
            </h1>
            <p className="text-xs sm:text-sm text-[#2c4e3e] leading-relaxed mb-6 font-normal">
              Measure real code energy, eliminate cloud compute waste, and automate green optimizations in your CI/CD pipeline.
            </p>
          </div>
        </div>

        {/* Bottom Metrics Showcase (Useful for both Code & Business) */}
        <div className="relative z-10 pb-1">
          
          {/* Twin Metric Cards */}
          <div className="grid grid-cols-2 gap-3 max-w-[420px] mb-3">
            
            {/* Metric Card 1: Carbon & Code Performance */}
            <div className="bg-white rounded-xl p-3.5 sm:p-4 border border-[#d3e7d8] shadow-xs flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-black text-[#0a291c] font-sans tracking-tight leading-none">
                  14.2
                </div>
                <div className="text-[11px] font-semibold text-slate-800 mt-1">
                  Carbon Score
                </div>
                <div className="text-[10px] text-[#467059]">
                  gCO₂e / 1k requests
                </div>
              </div>
              <svg className="w-12 sm:w-14 h-7 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
              </svg>
            </div>

            {/* Metric Card 2: Cloud Cost Savings */}
            <div className="bg-white rounded-xl p-3.5 sm:p-4 border border-[#d3e7d8] shadow-xs flex items-center justify-between">
              <div>
                <div className="text-xl sm:text-2xl font-black text-[#0a291c] font-sans tracking-tight leading-none">
                  -$340
                </div>
                <div className="text-[11px] font-semibold text-slate-800 mt-1">
                  Cloud Bill
                </div>
                <div className="text-[10px] text-[#467059]">
                  Monthly average saved
                </div>
              </div>
              <svg className="w-12 sm:w-14 h-7 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
              </svg>
            </div>

          </div>

          {/* Twin Minimal Global Standard Badges */}
          <div className="grid grid-cols-2 gap-3 max-w-[420px]">
            
            {/* Badge 1: Code Side */}
            <div className="bg-white/90 backdrop-blur-xs rounded-lg px-3 py-2 border border-[#d3e7d8] flex items-center gap-1.5 text-[11px] font-medium text-[#14422c]">
              <Check size={13} className="text-emerald-600 stroke-[3] shrink-0" />
              <span className="truncate">Automated Code Fixes</span>
            </div>

            {/* Badge 2: Business & Monitoring Side */}
            <div className="bg-white/90 backdrop-blur-xs rounded-lg px-3 py-2 border border-[#d3e7d8] flex items-center gap-1.5 text-[11px] font-medium text-[#14422c]">
              <Check size={13} className="text-emerald-600 stroke-[3] shrink-0" />
              <span className="truncate">Continuous Cost Audits</span>
            </div>

          </div>

        </div>

      </div>


      {/* ════════════════════════ RIGHT LOGIN CARD PANE ════════════════════════ */}
      <div className="lg:w-1/2 bg-[#fcfdfc] px-6 py-6 sm:py-8 flex items-center justify-center relative h-full overflow-hidden">
        
        <div className="w-full max-w-[380px]">
          
          {/* Main Floating Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-900/5 p-6 sm:p-7">
            
            {/* Header */}
            <div className="text-center mb-4 sm:mb-5">
              <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
                Welcome back
              </h2>
              <p className="text-xs text-slate-500 mt-1">
                Please enter your details to sign in
              </p>
            </div>

            {/* Error Banner */}
            {error && (
              <div className="mb-3 rounded-lg bg-rose-50 border border-rose-200 p-2.5 text-xs text-rose-700 flex items-start gap-2 animate-in fade-in" role="alert">
                <AlertCircle size={14} className="shrink-0 mt-0.5 text-rose-600" />
                <span className="leading-relaxed">{error}</span>
              </div>
            )}

            {/* Provider Buttons */}
            <div className="space-y-2 mb-4">
              
              {/* GitHub Button */}
              <button
                type="button"
                onClick={handleGitHubQuick}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-full border border-slate-300 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition shadow-2xs cursor-pointer"
              >
                <Github size={14} className="text-slate-900" />
                <span>Continue with GitHub</span>
              </button>

              {/* Google Button */}
              <button
                type="button"
                onClick={handleGoogleQuick}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-full border border-slate-300 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition shadow-2xs cursor-pointer"
              >
                <svg width="14" height="14" viewBox="0 0 24 24" className="shrink-0">
                  <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                  <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z" />
                  <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.17 0 9.97 0 12s.45 3.83 1.25 5.42l4.03-3.15Z" />
                  <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z" />
                </svg>
                <span>Continue with Google</span>
              </button>

            </div>

            {/* Divider */}
            <div className="relative flex py-0.5 items-center mb-3">
              <div className="flex-grow border-t border-slate-200"></div>
              <span className="shrink-0 mx-3 text-[11px] text-slate-400 font-normal">
                or sign in with email
              </span>
              <div className="flex-grow border-t border-slate-200"></div>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-3">
              
              {/* Email */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  Email
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  className="w-full px-3 py-2 text-xs sm:text-sm text-slate-800 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition shadow-2xs"
                />
              </div>

              {/* Password / Token */}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold text-slate-700">
                    Password
                  </label>
                  <a
                    href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] text-slate-500 hover:text-slate-800 transition"
                  >
                    Forgot password?
                  </a>
                </div>
                
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={passwordOrToken}
                    onChange={(e) => setPasswordOrToken(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-3 py-2 pr-9 text-xs sm:text-sm font-mono text-slate-800 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition shadow-2xs"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600 cursor-pointer"
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* Primary Sign In Button */}
              <button
                type="submit"
                disabled={loading}
                className="w-full mt-1.5 py-2.5 px-4 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs sm:text-sm font-semibold transition shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? (
                  <Loader2 size={15} className="animate-spin text-white" />
                ) : (
                  <span>Sign In</span>
                )}
              </button>

            </form>

            {/* Single Sign-On (SSO) */}
            <div className="text-center mt-3">
              <button
                type="button"
                onClick={handleSSO}
                className="text-xs font-semibold text-slate-700 hover:text-slate-900 transition cursor-pointer"
              >
                Single Sign-On (SSO)
              </button>
            </div>

          </div>

          {/* Simple, Non-Jargon Privacy Assurance Footnote */}
          <p className="text-center text-[11px] text-slate-400 mt-3 font-normal">
            Private &amp; secure &middot; Credentials are never stored on our servers
          </p>

        </div>

      </div>

    </div>
  );
}
