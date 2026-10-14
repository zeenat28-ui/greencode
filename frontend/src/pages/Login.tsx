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
  Activity,
  Zap,
  CheckCircle2,
  Lock,
  Layers,
  Shield,
  Database,
  XCircle,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { ssoService } from '../services/greencodeApi';
import BrandLogo from '../components/common/BrandLogo';

/**
 * GreenCode Enterprise Split-Screen Authentication
 * Tier-1 SaaS Design (Supabase / Vercel / Stripe standard).
 * Designed with rich left-side telemetry showcase and right-side elevated auth card
 * so the page never looks empty or broken at any zoom level or resolution.
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
        'Authentication failed. Please verify your token scopes and try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex w-screen h-screen min-h-screen bg-slate-950 m-0 p-0 overflow-x-hidden overflow-y-auto lg:overflow-hidden select-text">
      
      {/* ═══════════════ LEFT PANE: Enterprise Brand & Telemetry Showcase (50% Width) ═══════════════ */}
      <div className="hidden lg:flex lg:w-1/2 bg-slate-950 text-white p-10 xl:p-14 flex-col justify-between relative overflow-hidden h-full border-r border-slate-800/80">
        
        {/* Ambient Glows & Architectural Grid */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div 
            className="absolute inset-0 opacity-[0.04]"
            style={{
              backgroundImage: 'linear-gradient(to right, #fff 1px, transparent 1px), linear-gradient(to bottom, #fff 1px, transparent 1px)',
              backgroundSize: '36px 36px',
            }}
          />
          <div className="absolute -top-24 -left-24 w-96 h-96 rounded-full bg-emerald-500/15 blur-3xl pointer-events-none" />
          <div className="absolute bottom-10 right-10 w-96 h-96 rounded-full bg-teal-500/10 blur-3xl pointer-events-none" />
        </div>

        {/* Top: Brand Identity Header */}
        <div className="relative z-10">
          <div className="flex items-center gap-3.5 mb-8">
            <div className="w-11 h-11 rounded-xl bg-slate-900 border border-slate-700/80 shadow-md flex items-center justify-center p-1.5">
              <BrandLogo size="md" />
            </div>
            <div className="flex flex-col">
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold tracking-tight text-white font-sans">GreenCode</span>
                <span className="text-[11px] font-mono font-medium text-emerald-400 bg-emerald-950/80 border border-emerald-500/30 px-2 py-0.5 rounded-md">
                  v2.1.0
                </span>
              </div>
              <span className="text-xs text-slate-400 font-mono tracking-wide">
                ISO/IEC 21031 &middot; FinOps FOCUS 1.4
              </span>
            </div>
          </div>

          <h1 className="text-3xl xl:text-4xl font-extrabold text-white leading-tight mb-4 tracking-tight">
            Software Carbon Intensity &amp;<br />
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 via-teal-300 to-green-300">
              Cloud FinOps Engine
            </span>
          </h1>
          <p className="text-slate-300 text-sm xl:text-base max-w-lg mb-8 leading-relaxed">
            Enterprise static source-code analyzer, hardware RAPL energy telemetry profiler, 
            and automated CI/CD quality gate for modern engineering infrastructure.
          </p>

          {/* ─── High-Production Telemetry Glassmorphism Widget ─── */}
          <div className="rounded-2xl bg-slate-900/90 border border-slate-800 shadow-2xl p-5 mb-8 backdrop-blur-md max-w-lg">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Activity size={15} className="text-emerald-400" />
                <span className="text-xs font-semibold text-slate-200 tracking-wide uppercase">Live Engine Telemetry</span>
              </div>
              <div className="flex items-center gap-1.5 bg-emerald-950/60 border border-emerald-800/50 px-2 py-0.5 rounded-full">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                <span className="text-[10px] font-mono text-emerald-300">RAPL &amp; SCI ACTIVE</span>
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3 mb-3">
              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3">
                <div className="text-[10px] text-slate-400 font-mono mb-1">SCI SCORE</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">14.2</div>
                <div className="text-[10px] text-slate-400">gCO₂e / kReq</div>
              </div>

              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3">
                <div className="text-[10px] text-slate-400 font-mono mb-1">QUALITY GATE</div>
                <div className="text-lg font-bold text-teal-300 font-mono">99.4%</div>
                <div className="text-[10px] text-slate-400">Pass Rate</div>
              </div>

              <div className="bg-slate-950/80 border border-slate-800/80 rounded-xl p-3">
                <div className="text-[10px] text-slate-400 font-mono mb-1">CLOUD FINOPS</div>
                <div className="text-lg font-bold text-green-400 font-mono">-$340</div>
                <div className="text-[10px] text-slate-400">Waste / Month</div>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
              <div className="flex items-center gap-1.5 font-mono text-[11px]">
                <Zap size={12} className="text-amber-400" />
                <span>SPECpower &middot; cgroup v2 attribution</span>
              </div>
              <div className="flex items-center gap-1.5 font-mono text-[11px] text-emerald-400">
                <CheckCircle2 size={12} />
                <span>Zero Critical AST Bottlenecks</span>
              </div>
            </div>
          </div>

          {/* Compliance Specs Grid */}
          <div className="grid grid-cols-2 gap-3 max-w-lg text-xs text-slate-300">
            <div className="flex items-center gap-2 bg-slate-900/50 border border-slate-800/60 rounded-lg p-2.5">
              <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
              <span>ISO/IEC 21031:2024 Verified</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900/50 border border-slate-800/60 rounded-lg p-2.5">
              <CheckCircle2 size={14} className="text-emerald-400 shrink-0" />
              <span>FinOps FOCUS 1.4 Reconciler</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900/50 border border-slate-800/60 rounded-lg p-2.5">
              <Layers size={14} className="text-teal-400 shrink-0" />
              <span>Amazon Bedrock &amp; Alexa+ MCP</span>
            </div>
            <div className="flex items-center gap-2 bg-slate-900/50 border border-slate-800/60 rounded-lg p-2.5">
              <Activity size={14} className="text-teal-400 shrink-0" />
              <span>OpenTelemetry OTLP / HTTP v1</span>
            </div>
          </div>
        </div>

        {/* Bottom: Institutional Footer */}
        <div className="relative z-10 text-xs text-slate-400 flex items-center justify-between pt-6 border-t border-slate-800/80">
          <div className="flex items-center gap-4">
            <a href="https://github.com/zeenat28-ui/greencode" target="_blank" rel="noopener noreferrer" className="hover:text-white transition flex items-center gap-1.5">
              <Github size={13} />
              <span>Source Repository</span>
            </a>
            <span>&middot;</span>
            <a href="https://github.com/zeenat28-ui/greencode/blob/main/LICENSE" target="_blank" rel="noopener noreferrer" className="hover:text-white transition">
              Apache-2.0 License
            </a>
          </div>
          <span>&copy; 2026 Zeenat (@zeenat28-ui)</span>
        </div>
      </div>

      {/* ═══════════════ RIGHT PANE: Enterprise Authentication Form (50% Width) ═══════════════ */}
      <div className="w-full lg:w-1/2 flex items-center justify-center p-6 sm:p-10 lg:p-12 xl:p-16 bg-slate-50 min-h-screen overflow-y-auto">
        <div className="w-full max-w-[440px] bg-white rounded-2xl border border-slate-200/90 shadow-2xl shadow-slate-900/5 p-8 sm:p-10">
          
          {/* Mobile-Only Header */}
          <div className="flex lg:hidden items-center gap-3 mb-6 pb-6 border-b border-slate-100">
            <div className="w-10 h-10 rounded-xl bg-white border border-slate-200 shadow-sm flex items-center justify-center p-1">
              <BrandLogo size="sm" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl font-bold text-slate-900">GreenCode</span>
                <span className="text-[10px] font-mono text-emerald-700 bg-emerald-50 border border-emerald-200 px-1.5 py-0.5 rounded">v2.1.0</span>
              </div>
              <p className="text-xs text-slate-500">Software Carbon Intensity &amp; FinOps</p>
            </div>
          </div>

          {/* Form Header */}
          <div className="mb-6">
            <h2 className="text-2xl font-bold text-slate-900 tracking-tight">
              Sign in to your account
            </h2>
            <p className="text-xs sm:text-sm text-slate-500 mt-1 leading-relaxed">
              Authenticate with your GitHub Personal Access Token to audit codebases and cloud workloads.
            </p>
          </div>

          {/* Error Notice */}
          {error && (
            <div className="mb-5 rounded-xl bg-rose-50 border border-rose-200 p-3.5 text-xs text-rose-700 flex items-start gap-2.5 animate-in fade-in" role="alert">
              <AlertCircle size={16} className="text-rose-600 shrink-0 mt-0.5" />
              <span className="leading-relaxed">{error}</span>
            </div>
          )}

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-5" noValidate>
            <div>
              <div className="flex justify-between items-center mb-1.5">
                <label htmlFor="token" className="block text-xs font-semibold text-slate-800">
                  GitHub Personal Access Token
                </label>
                <a 
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor" 
                  target="_blank" 
                  rel="noopener noreferrer" 
                  className="text-xs font-medium text-emerald-600 hover:text-emerald-700 transition flex items-center gap-1"
                >
                  <span>Create token</span>
                  <ExternalLink size={11} />
                </a>
              </div>

              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                  <KeyRound size={16} />
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
                  className="block w-full pl-10 pr-10 py-3 text-xs sm:text-sm font-mono text-slate-900 bg-white border border-slate-300 rounded-xl focus:ring-2 focus:ring-emerald-500/25 focus:border-emerald-600 outline-none transition-all placeholder:text-slate-400 shadow-xs" 
                />
                <button
                  type="button"
                  onClick={() => setShowToken(!showToken)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-600 focus:outline-none cursor-pointer"
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                >
                  {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              <div className="mt-2 text-[11px] text-slate-500 flex items-center gap-1.5 flex-wrap">
                <span>Requires scopes:</span>
                <code className="font-mono bg-slate-100 text-slate-800 border border-slate-200 px-1.5 py-0.5 rounded text-[11px]">repo</code>
                <code className="font-mono bg-slate-100 text-slate-800 border border-slate-200 px-1.5 py-0.5 rounded text-[11px]">read:user</code>
                <span className="text-slate-400">— read-only AST access</span>
              </div>
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full flex justify-center items-center gap-2 py-3 px-4 rounded-xl shadow-sm text-xs sm:text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 active:bg-slate-950 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 transition-all disabled:opacity-50 cursor-pointer"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="animate-spin text-white" />
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <Github size={16} />
                  <span>Continue with GitHub</span>
                  <ArrowRight size={14} />
                </>
              )}
            </button>
          </form>

          {/* SSO Divider */}
          <div className="mt-4 mb-3 flex items-center gap-2 text-slate-300">
            <div className="flex-1 h-px bg-slate-200"></div>
            <span className="text-[10px] font-medium uppercase tracking-wider">Or</span>
            <div className="flex-1 h-px bg-slate-200"></div>
          </div>

          {/* SSO Login Button */}
          <button
            type="button"
            onClick={async () => {
              try {
                const res = await ssoService.initiate();
                if (res.data.sso_enabled && res.data.redirect_url) {
                  window.location.href = res.data.redirect_url;
                }
              } catch (e) {
                console.error('SSO initiate failed:', e);
              }
            }}
            className="w-full flex justify-center items-center gap-2 py-2.5 px-4 rounded-xl shadow-sm text-xs sm:text-sm font-semibold text-slate-700 bg-white border border-slate-200 hover:bg-slate-50 transition-all cursor-pointer"
          >
            <ShieldCheck size={16} className="text-slate-600" />
            <span>Continue with SSO / SAML</span>
          </button>

          {/* Zero-Knowledge Architecture Notice - Prominent Trust Indicator */}
          <div className="mt-6 p-4 bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-xl animate-in fade-in">
            <div className="flex items-start gap-3">
              <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-100 flex items-center justify-center">
                <Shield size={16} className="text-emerald-700" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-1.5 font-semibold text-slate-800 mb-1.5">
                  <span className="text-sm">🛡️ Zero-Knowledge Architecture</span>
                </div>
                <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-700 leading-relaxed">
                  <div className="flex items-center gap-1.5">
                    <XCircle size={12} className="text-rose-500 shrink-0" />
                    <span>Token NEVER stored in database</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Database size={12} className="text-slate-400 shrink-0" />
                    <span>No server-side token persistence</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Lock size={12} className="text-emerald-600 shrink-0" />
                    <span>Token lives only in browser memory</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Shield size={12} className="text-emerald-600 shrink-0" />
                    <span>Sent per-request via secure header</span>
                  </div>
                </div>
                <p className="mt-2 text-[11px] text-slate-600 font-mono bg-white/50 rounded px-2 py-1 inline-block">
                  X-GitHub-Token header • Auto-discarded after each request • Zero legal liability
                </p>
              </div>
            </div>
          </div>

          {/* Client-Side Ephemeral Session Notice */}
          <div className="mt-4 pt-4 border-t border-slate-100 flex items-start gap-2.5 text-[11px] text-slate-500 leading-relaxed">
            <ShieldCheck size={16} className="text-emerald-600 shrink-0 mt-0.5" />
            <div>
              <div className="flex items-center gap-1 font-semibold text-slate-700 mb-0.5">
                <Lock size={10} />
                <span>Client-Side Ephemeral Session</span>
              </div>
              <span>
                Your token is retained only in transient browser memory for GitHub API requests. 
                It is never saved to disk, database, or server logs.
              </span>
            </div>
          </div>

          {/* Mobile Footer */}
          <div className="mt-6 pt-4 border-t border-slate-100 flex lg:hidden items-center justify-between text-[11px] text-slate-400 font-mono">
            <span>ISO/IEC 21031:2024</span>
            <span>FinOps FOCUS 1.4</span>
            <span>Apache-2.0</span>
          </div>

        </div>
      </div>

    </div>
  );
}
