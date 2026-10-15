import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { Eye, EyeOff, Loader2, AlertCircle, Check, Github } from 'lucide-react';
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
    const token = passwordOrToken.trim() || email.trim() || 'demo';
    performLogin(token);
  };

  const handleGitHubQuick = () => {
    const token = passwordOrToken.trim() || 'demo';
    performLogin(token);
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
      
      {/* ════════════════════════ LEFT HERO PANE (Mint Green with Steel Shine) ════════════════════════ */}
      <div className="lg:w-1/2 bg-[linear-gradient(135deg,#e5f3e8_0%,#edf7f1_20%,#ffffff_38%,#dceddf_46%,#f4faf6_65%,#e8f4ec_85%,#edf7f0_100%)] shadow-[inset_0_1px_2px_0_rgba(255,255,255,0.95),inset_0_-1px_1px_0_rgba(14,72,47,0.08),inset_-1px_0_0_0_rgba(255,255,255,0.7)] px-8 sm:px-12 xl:px-16 py-6 sm:py-8 lg:py-10 flex flex-col justify-between relative overflow-hidden border-b lg:border-b-0 lg:border-r border-[#b8dcbf] h-full">
        
        {/* Steel Sheen Specular Glare Highlights (Maintains #ebf6ee with Metallic Shine) */}
        <div className="absolute inset-0 pointer-events-none select-none bg-[linear-gradient(115deg,transparent_20%,rgba(255,255,255,0.22)_35%,rgba(255,255,255,0.42)_42%,rgba(255,255,255,0.08)_50%,transparent_65%)]" />
        <div className="absolute inset-0 pointer-events-none select-none bg-[radial-gradient(ellipse_80%_60%_at_65%_25%,rgba(255,255,255,0.4)_0%,rgba(255,255,255,0.12)_40%,transparent_70%)]" />

        {/* Subtle Geometric Wireframe Leaf + Cloud Line Art Overlay (Pushed Right Against Card Boundary) */}
        <div className="absolute right-[-10px] lg:right-0 top-6 lg:top-10 w-[300px] sm:w-[330px] h-[300px] pointer-events-none select-none opacity-50 text-[#2f6645]">
          <svg viewBox="0 0 320 300" fill="none" stroke="currentColor" strokeWidth="1.3" className="w-full h-full">
            {/* ═════════ 1. COMPLETE CLOUD ON LEFT (Background, 100% Fully Visible Even in Overlap) ═════════ */}
            <path 
              d="M 214.0 124.2 C 210.9 108.3 196.9 96.4 180.2 96.4 C 166.9 96.4 155.4 103.9 149.6 115.0 C 135.8 116.5 125.0 128.2 125.0 142.4 C 125.0 157.6 137.4 170.0 152.6 170.0 L 212.4 170.0 C 225.1 170.0 235.4 159.7 235.4 147.0 C 235.4 134.9 226.0 125.0 214.0 124.2 Z" 
              strokeWidth="1.4"
            />
            {/* Cloud Internal Tech Pulse Node */}
            <path d="M 180.2 155 L 180.2 130 M 175 135 L 180.2 130 L 185.4 135" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" opacity="0.65" />
            <circle cx="180.2" cy="155" r="2.2" fill="currentColor" opacity="0.8" />

            {/* ═════════ 2. TECH LEAF ON RIGHT (Wireframe Hugging Right Card Boundary, Zero Opaque Fill) ═════════ */}
            <path 
              d="M 252 40 C 312 95 312 210 252 265 C 192 210 192 95 252 40 Z" 
              strokeWidth="1.5"
            />
            
            {/* Central Leaf Stem */}
            <path d="M 252 40 L 252 265" strokeWidth="1.4" />
            
            {/* Vein Branch Lines */}
            {/* Pair 1 */}
            <path d="M 252 84 L 231 70" strokeWidth="1.2" />
            <path d="M 252 84 L 273 70" strokeWidth="1.2" />

            {/* Pair 2 */}
            <path d="M 252 122 L 215 108" strokeWidth="1.2" />
            <path d="M 252 122 L 289 108" strokeWidth="1.2" />

            {/* Pair 3 (Widest) */}
            <path d="M 252 162 L 209 150" strokeWidth="1.2" />
            <path d="M 252 162 L 295 150" strokeWidth="1.2" />

            {/* Pair 4 */}
            <path d="M 252 204 L 215 192" strokeWidth="1.2" />
            <path d="M 252 204 L 289 192" strokeWidth="1.2" />

            {/* Pair 5 */}
            <path d="M 252 240 L 231 232" strokeWidth="1.2" />
            <path d="M 252 240 L 273 232" strokeWidth="1.2" />

            {/* ═════════ TECH DOTS AT EVERY SINGLE LINE END (Terminal Nodes) ═════════ */}
            {/* Stem Terminals */}
            <circle cx="252" cy="40" r="3" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="252" cy="265" r="3" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Vein Pair 1 Dots */}
            <circle cx="231" cy="70" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="273" cy="70" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Vein Pair 2 Dots */}
            <circle cx="215" cy="108" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="289" cy="108" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Vein Pair 3 Dots */}
            <circle cx="209" cy="150" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="295" cy="150" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Vein Pair 4 Dots */}
            <circle cx="215" cy="192" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="289" cy="192" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Vein Pair 5 Dots */}
            <circle cx="231" cy="232" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="273" cy="232" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />

            {/* Stem Junction Internal Circuit Nodes */}
            <circle cx="252" cy="84" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="122" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="162" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="204" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="240" r="2" fill="currentColor" opacity="0.65" />
          </svg>
        </div>

        {/* Top: Brand Logo & Title */}
        <div className="relative z-10 pt-1">
          <div className="flex items-center gap-2.5">
            <img 
              src="/logo.png" 
              alt="GreenCode" 
              className="w-8 h-8 object-contain select-none shrink-0" 
            />
            <span className="text-xl font-bold tracking-tight text-[#0a291c]">
              GreenCode
            </span>
          </div>
        </div>

        {/* Middle Core Area: Hero + Cards Pulled Higher Up (Eliminates Empty Space) */}
        <div className="relative z-10 my-auto py-2">
          
          {/* Headline & Clear Value-Driven Body Text */}
          <div className="max-w-[540px] mb-5 sm:mb-6">
            <h1 className="text-4xl sm:text-[46px] lg:text-[50px] font-black text-[#0a291c] tracking-tight mb-4 flex flex-col gap-1.5 sm:gap-2 leading-none">
              <span>BUILD GREENER</span>
              <span>RUN LEANER</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#2c4e3e] leading-relaxed font-normal max-w-[480px]">
              Measure real code energy, eliminate cloud compute waste, and automate green optimizations in your CI/CD pipeline.
            </p>
          </div>

          {/* Cards & Badges Section: Expanded Width + Generous Gap between Cards */}
          <div className="w-full max-w-[540px] space-y-3.5">
            
            {/* Twin Metric Cards with Generous Spacing and Steel Sheen */}
            <div className="grid grid-cols-2 gap-4 sm:gap-5 w-full">
              
              {/* Metric Card 1: Carbon & Code Performance */}
              <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 hover:shadow-[0_6px_20px_rgba(14,72,47,0.1),inset_0_1px_2px_rgba(255,255,255,1)] transition">
                <div>
                  <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
                    14.2
                  </div>
                  <div className="text-xs font-semibold text-slate-800 mt-1.5">
                    Carbon Score
                  </div>
                  <div className="text-[11px] text-[#467059]">
                    gCO₂e / 1k requests
                  </div>
                </div>
                <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                  <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
                </svg>
              </div>

              {/* Metric Card 2: Cloud Cost Savings */}
              <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 hover:shadow-[0_6px_20px_rgba(14,72,47,0.1),inset_0_1px_2px_rgba(255,255,255,1)] transition">
                <div>
                  <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">
                    -$340
                  </div>
                  <div className="text-xs font-semibold text-slate-800 mt-1.5">
                    Cloud Bill
                  </div>
                  <div className="text-[11px] text-[#467059]">
                    Monthly average saved
                  </div>
                </div>
                <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                  <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
                </svg>
              </div>

            </div>

            {/* Twin Badges Spanning Balanced Full Width */}
            <div className="grid grid-cols-2 gap-4 sm:gap-5 w-full">
              
              {/* Badge 1: Code Side */}
              <div className="bg-[linear-gradient(145deg,rgba(255,255,255,0.95)_0%,rgba(240,248,243,0.85)_100%)] backdrop-blur-xs rounded-xl px-4 py-2.5 border border-white/80 shadow-[0_2px_8px_rgba(14,72,47,0.04),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center gap-2 text-xs font-medium text-[#14422c]">
                <Check size={14} className="text-emerald-600 stroke-[3] shrink-0" />
                <span className="truncate">Automated Code Fixes</span>
              </div>

              {/* Badge 2: Business & Monitoring Side */}
              <div className="bg-[linear-gradient(145deg,rgba(255,255,255,0.95)_0%,rgba(240,248,243,0.85)_100%)] backdrop-blur-xs rounded-xl px-4 py-2.5 border border-white/80 shadow-[0_2px_8px_rgba(14,72,47,0.04),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center gap-2 text-xs font-medium text-[#14422c]">
                <Check size={14} className="text-emerald-600 stroke-[3] shrink-0" />
                <span className="truncate">Continuous Cost Audits</span>
              </div>

            </div>

          </div>

        </div>

        {/* Bottom spacer for balanced vertical alignment */}
        <div className="h-2"></div>

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
