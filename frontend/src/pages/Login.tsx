import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Eye, EyeOff, Loader2, AlertCircle, Check, Github, KeyRound, X, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { authService } from '../services/greencodeApi';
import LegalModal from '../components/LegalModal';

// ---------------------------------------------------------------------------
// Google GSI type shim – the real accounts.google.com/gsi/client injects this
// ---------------------------------------------------------------------------
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential: string; select_by: string }) => void;
            auto_select?: boolean;
            cancel_on_tap_outside?: boolean;
            use_fedcm_for_prompt?: boolean;
          }) => void;
          prompt: (notification?: (n: { isNotDisplayed: () => boolean; isSkippedMoment: () => boolean; getDismissedReason: () => string }) => void) => void;
          renderButton: (
            parent: HTMLElement,
            options: {
              type?: string;
              theme?: string;
              size?: string;
              width?: number;
              shape?: string;
              text?: string;
            }
          ) => void;
          cancel: () => void;
          disableAutoSelect: () => void;
        };
      };
    };
  }
}

// ---------------------------------------------------------------------------
// GitHub OAuth popup helper
// ---------------------------------------------------------------------------
const GITHUB_POPUP_NAME = 'github_oauth_popup';
const POPUP_W = 600;
const POPUP_H = 700;

function openGitHubPopup(authUrl: string): Window | null {
  const left = window.screenX + (window.outerWidth - POPUP_W) / 2;
  const top = window.screenY + (window.outerHeight - POPUP_H) / 2;
  return window.open(
    authUrl,
    GITHUB_POPUP_NAME,
    `width=${POPUP_W},height=${POPUP_H},left=${left},top=${top},toolbar=0,menubar=0,scrollbars=1`
  );
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------
export default function Login() {
  const { loginWithEmail, registerWithEmail, loginWithGoogleToken, loginWithGoogleCode, loginWithGitHubCode, connectGitHub, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from || '/dashboard';

  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [passwordOrToken, setPasswordOrToken] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isSignUp, setIsSignUp] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  // Legal Modal
  const [legalModalOpen, setLegalModalOpen] = useState(false);
  const [legalModalTab, setLegalModalTab] = useState<'terms' | 'privacy'>('terms');

  // Forgot Password Modal
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forgotEmail, setForgotEmail] = useState('');
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotMessage, setForgotMessage] = useState<string | null>(null);
  const [receivedResetToken, setReceivedResetToken] = useState<string | null>(null);
  const [newPasswordVal, setNewPasswordVal] = useState('');
  const [resetSuccessMsg, setResetSuccessMsg] = useState<string | null>(null);

  // GitHub PAT Fallback Modal State
  const [githubPatModalOpen, setGithubPatModalOpen] = useState(false);
  const [githubPatVal, setGithubPatVal] = useState('');
  const [githubPatLoading, setGithubPatLoading] = useState(false);
  const [githubPatError, setGithubPatError] = useState<string | null>(null);

  const githubPopupRef = useRef<Window | null>(null);
  const githubPollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const googleButtonRef = useRef<HTMLButtonElement | null>(null);

  // -------------------------------------------------------------------------
  // Handle OAuth callback: ?code=xxx&provider=github  (popup or redirect)
  // -------------------------------------------------------------------------
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const code = params.get('code');
    const provider = params.get('provider') || params.get('state')?.split(':')[0];

    if (!code) return;

    // If we are inside a popup, send the code to the opener and close
    if (window.opener && window.name === GITHUB_POPUP_NAME) {
      window.opener.postMessage({ type: 'github_oauth', code }, window.location.origin);
      window.close();
      return;
    }

    // Full-page redirect flow fallback (no popup)
    if (provider === 'google') {
      (async () => {
        setGoogleLoading(true);
        setError(null);
        try {
          const redirectUri = `${window.location.origin}/login?provider=google`;
          await loginWithGoogleCode(code, redirectUri);
          navigate(from, { replace: true });
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } }; message?: string };
          setError(e?.response?.data?.detail || e?.message || 'Google authentication failed.');
        } finally {
          setGoogleLoading(false);
        }
      })();
    } else if (provider === 'github' || !provider) {
      (async () => {
        setGithubLoading(true);
        setError(null);
        try {
          const redirectUri = `${window.location.origin}/login`;
          await loginWithGitHubCode(code, redirectUri);
          navigate(from, { replace: true });
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } }; message?: string };
          setError(e?.response?.data?.detail || e?.message || 'GitHub authentication failed.');
        } finally {
          setGithubLoading(false);
        }
      })();
    }
  }, [location.search]); // eslint-disable-line react-hooks/exhaustive-deps

  // -------------------------------------------------------------------------
  // Listen for GitHub popup postMessage
  // -------------------------------------------------------------------------
  useEffect(() => {
    const handler = async (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return;
      if (event.data?.type !== 'github_oauth') return;

      const code: string = event.data.code;
      setGithubLoading(true);
      setError(null);
      try {
        const redirectUri = `${window.location.origin}/login`;
        await loginWithGitHubCode(code, redirectUri);
        navigate(from, { replace: true });
      } catch (err: unknown) {
        const e = err as { response?: { data?: { detail?: string } }; message?: string };
        setError(e?.response?.data?.detail || e?.message || 'GitHub authentication failed.');
      } finally {
        setGithubLoading(false);
      }
    };

    window.addEventListener('message', handler);
    return () => window.removeEventListener('message', handler);
  }, [from, loginWithGitHubCode, navigate]);

  // -------------------------------------------------------------------------
  // Cleanup popup poll on unmount
  // -------------------------------------------------------------------------
  useEffect(() => {
    return () => {
      if (githubPollRef.current) clearInterval(githubPollRef.current);
    };
  }, []);

  // -------------------------------------------------------------------------
  // GitHub OAuth button
  // -------------------------------------------------------------------------
  const handleGitHubQuick = async () => {
    if (githubLoading) return;
    setError(null);
    setGithubLoading(true);

    try {
      const redirectUri = `${window.location.origin}/login`;
      const res = await authService.getGitHubAuthorize(redirectUri);

      if (res.data.configured && res.data.auth_url) {
        // Real OAuth: open a popup window pointing to GitHub
        const popup = openGitHubPopup(res.data.auth_url);
        githubPopupRef.current = popup;

        if (!popup) {
          // Popup was blocked – fall back to redirect
          window.location.href = res.data.auth_url;
          return;
        }

        // Poll until the popup closes (handles user who manually closes it)
        if (githubPollRef.current) clearInterval(githubPollRef.current);
        githubPollRef.current = setInterval(() => {
          if (popup.closed) {
            clearInterval(githubPollRef.current!);
            githubPollRef.current = null;
            setGithubLoading(false);
          }
        }, 500);
      } else {
        // GitHub OAuth not configured in .env — open the GitHub PAT / setup dialog
        setGithubLoading(false);
        setGithubPatModalOpen(true);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setError(e?.response?.data?.detail || e?.message || 'GitHub authentication failed.');
      setGithubLoading(false);
    }
  };

  const handleGitHubPatSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const token = githubPatVal.trim();
    if (!token) {
      setGithubPatError('Please enter your GitHub Personal Access Token.');
      return;
    }
    setGithubPatLoading(true);
    setGithubPatError(null);
    try {
      await connectGitHub(token);
      setGithubPatModalOpen(false);
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setGithubPatError(e?.response?.data?.detail || e?.message || 'Invalid GitHub token. Please verify permissions.');
    } finally {
      setGithubPatLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Google OAuth button — uses Google Identity Services (GSI) real popup
  // -------------------------------------------------------------------------
  const handleGoogleQuick = () => {
    if (googleLoading) return;
    setError(null);

    const clientId = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined;

    if (!clientId) {
      setError(
        'Google OAuth is not configured. Add VITE_GOOGLE_CLIENT_ID to frontend/.env and restart the dev server.'
      );
      return;
    }

    if (!window.google?.accounts?.id) {
      setError('Google Identity Services library is still loading. Please try again in a moment.');
      return;
    }

    setGoogleLoading(true);

    window.google.accounts.id.initialize({
      client_id: clientId,
      callback: async (response) => {
        // response.credential is a real Google ID token (JWT)
        if (!response.credential) {
          setError('Google sign-in was cancelled or failed. Please try again.');
          setGoogleLoading(false);
          return;
        }
        try {
          await loginWithGoogleToken(response.credential);
          navigate(from, { replace: true });
        } catch (err: unknown) {
          const e = err as { response?: { data?: { detail?: string } }; message?: string };
          setError(e?.response?.data?.detail || e?.message || 'Google authentication failed.');
        } finally {
          setGoogleLoading(false);
        }
      },
      auto_select: false,
      cancel_on_tap_outside: true,
    });

    // Show the One Tap UI
    window.google.accounts.id.prompt(async (notification) => {
      if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
        // One Tap was suppressed or dismissed — fallback seamlessly to Google OAuth redirect
        try {
          const redirectUri = `${window.location.origin}/login?provider=google`;
          const res = await authService.getGoogleAuthorize(redirectUri);
          if (res.data?.auth_url) {
            window.location.href = res.data.auth_url;
            return;
          }
        } catch {
          // fallback failed, try in-place button render
        }
        if (googleButtonRef.current) {
          googleButtonRef.current.innerHTML = '';
          window.google!.accounts.id.renderButton(googleButtonRef.current, {
            type: 'standard',
            theme: 'outline',
            size: 'large',
            width: googleButtonRef.current.offsetWidth,
            shape: 'pill',
            text: isSignUp ? 'signup_with' : 'signin_with',
          });
        }
        setGoogleLoading(false);
      }
    });
  };

  // -------------------------------------------------------------------------
  // Email / password submit
  // -------------------------------------------------------------------------
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanEmail = email.trim();
    const cleanPassword = passwordOrToken.trim();

    if (!cleanEmail) { setError('Please enter a valid email address.'); return; }
    if (!cleanPassword) { setError('Please enter your password.'); return; }

    setLoading(true);
    try {
      if (isSignUp) {
        if (cleanPassword.length < 6) {
          setError('Password must be at least 6 characters long.');
          setLoading(false);
          return;
        }
        await registerWithEmail(cleanEmail, cleanPassword, fullName.trim() || undefined);
      } else {
        await loginWithEmail(cleanEmail, cleanPassword);
      }
      navigate(from, { replace: true });
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      const detail = e?.response?.data?.detail || e?.message || 'Authentication failed. Please verify your credentials.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  // -------------------------------------------------------------------------
  // Forgot password handlers
  // -------------------------------------------------------------------------
  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!forgotEmail.trim()) return;
    setForgotLoading(true);
    setForgotMessage(null);
    try {
      const res = await authService.forgotPassword(forgotEmail.trim());
      setForgotMessage(res.data.message);
      if (res.data.reset_token) setReceivedResetToken(res.data.reset_token);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setForgotMessage(e?.response?.data?.detail || 'Failed to dispatch password reset request.');
    } finally {
      setForgotLoading(false);
    }
  };

  const handleResetPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!receivedResetToken || !newPasswordVal.trim()) return;
    setForgotLoading(true);
    try {
      const res = await authService.resetPassword(receivedResetToken, newPasswordVal.trim());
      setResetSuccessMsg(res.data.message);
      setTimeout(() => {
        setForgotModalOpen(false);
        setPasswordOrToken(newPasswordVal.trim());
        setEmail(forgotEmail.trim());
      }, 1500);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setForgotMessage(e?.response?.data?.detail || 'Failed to reset password.');
    } finally {
      setForgotLoading(false);
    }
  };

  const openLegal = (tab: 'terms' | 'privacy') => {
    setLegalModalTab(tab);
    setLegalModalOpen(true);
  };

  // -------------------------------------------------------------------------
  // Render
  // -------------------------------------------------------------------------
  return (
    <div className="h-screen max-h-screen w-screen overflow-hidden flex flex-col lg:flex-row bg-[#fbfcfa] font-sans text-slate-900 select-none">

      {/* ════════════════════════ LEFT HERO PANE (Vibrant Mint Green with Steel Shine) ════════════════════════ */}
      <div className="lg:w-1/2 bg-[linear-gradient(135deg,#c3eed0_0%,#d8f5e2_20%,#f0fcf5_38%,#b6e8c5_50%,#e4f9ec_70%,#c8f0d5_100%)] shadow-[inset_0_1px_2px_0_rgba(255,255,255,0.95),inset_0_-1px_1px_0_rgba(14,72,47,0.08),inset_-1px_0_0_0_rgba(255,255,255,0.7)] px-8 sm:px-12 xl:px-16 py-6 sm:py-8 lg:py-10 flex flex-col justify-between relative overflow-hidden border-b lg:border-b-0 lg:border-r border-[#9dd9aa] h-full">

        {/* Steel Sheen Specular Highlights */}
        <div className="absolute inset-0 pointer-events-none select-none bg-[linear-gradient(115deg,transparent_20%,rgba(255,255,255,0.22)_35%,rgba(255,255,255,0.42)_42%,rgba(255,255,255,0.08)_50%,transparent_65%)]" />
        <div className="absolute inset-0 pointer-events-none select-none bg-[radial-gradient(ellipse_80%_60%_at_65%_25%,rgba(255,255,255,0.4)_0%,rgba(255,255,255,0.12)_40%,transparent_70%)]" />

        {/* Wireframe Leaf + Cloud Line Art */}
        <div className="absolute right-[-10px] lg:right-0 top-6 lg:top-10 w-[300px] sm:w-[330px] h-[300px] pointer-events-none select-none opacity-50 text-[#2f6645]">
          <svg viewBox="0 0 320 300" fill="none" stroke="currentColor" strokeWidth="1.3" className="w-full h-full">
            <path d="M 214.0 124.2 C 210.9 108.3 196.9 96.4 180.2 96.4 C 166.9 96.4 155.4 103.9 149.6 115.0 C 135.8 116.5 125.0 128.2 125.0 142.4 C 125.0 157.6 137.4 170.0 152.6 170.0 L 212.4 170.0 C 225.1 170.0 235.4 159.7 235.4 147.0 C 235.4 134.9 226.0 125.0 214.0 124.2 Z" strokeWidth="1.4" />
            <path d="M 180.2 155 L 180.2 130 M 175 135 L 180.2 130 L 185.4 135" strokeWidth="1.3" strokeLinecap="round" strokeLinejoin="round" opacity="0.65" />
            <circle cx="180.2" cy="155" r="2.2" fill="currentColor" opacity="0.8" />
            <path d="M 252 40 C 312 95 312 210 252 265 C 192 210 192 95 252 40 Z" strokeWidth="1.5" />
            <path d="M 252 40 L 252 265" strokeWidth="1.4" />
            <path d="M 252 84 L 231 70" strokeWidth="1.2" /><path d="M 252 84 L 273 70" strokeWidth="1.2" />
            <path d="M 252 122 L 215 108" strokeWidth="1.2" /><path d="M 252 122 L 289 108" strokeWidth="1.2" />
            <path d="M 252 162 L 209 150" strokeWidth="1.2" /><path d="M 252 162 L 295 150" strokeWidth="1.2" />
            <path d="M 252 204 L 215 192" strokeWidth="1.2" /><path d="M 252 204 L 289 192" strokeWidth="1.2" />
            <path d="M 252 240 L 231 232" strokeWidth="1.2" /><path d="M 252 240 L 273 232" strokeWidth="1.2" />
            <circle cx="252" cy="40" r="3" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="252" cy="265" r="3" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="231" cy="70" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="273" cy="70" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="215" cy="108" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="289" cy="108" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="209" cy="150" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="295" cy="150" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="215" cy="192" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="289" cy="192" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="231" cy="232" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="273" cy="232" r="2.8" fill="#10b981" stroke="currentColor" strokeWidth="0.9" />
            <circle cx="252" cy="84" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="122" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="162" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="204" r="2" fill="currentColor" opacity="0.65" />
            <circle cx="252" cy="240" r="2" fill="currentColor" opacity="0.65" />
          </svg>
        </div>

        {/* Brand */}
        <div className="relative z-10 pt-1">
          <div className="flex items-center gap-2.5">
            <img src="/logo.png" alt="GreenCode" className="w-8 h-8 object-contain select-none shrink-0" />
            <span className="text-xl font-bold tracking-tight text-[#0a291c]">GreenCode</span>
          </div>
        </div>

        {/* Hero Copy + Stats */}
        <div className="relative z-10 my-auto py-2">
          <div className="max-w-[540px] mb-5 sm:mb-6">
            <h1 className="text-4xl sm:text-[46px] lg:text-[50px] font-black text-[#0a291c] tracking-tight mb-4 flex flex-col gap-1.5 sm:gap-2 leading-none">
              <span>BUILD GREENER</span>
              <span>RUN LEANER</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#2c4e3e] leading-relaxed font-normal max-w-[480px]">
              Measure real code energy, eliminate cloud compute waste, and automate green optimizations in your CI/CD pipeline.
            </p>
          </div>

          <div className="w-full max-w-[540px] space-y-3.5">
            <div className="grid grid-cols-2 gap-4 sm:gap-5 w-full">
              <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
                <div>
                  <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">14.2</div>
                  <div className="text-xs font-semibold text-slate-800 mt-1.5">Carbon Score</div>
                  <div className="text-[11px] text-[#467059]">gCO₂e / 1k requests</div>
                </div>
                <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                  <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M2 15 Q 15 25, 28 10 T 55 18 T 78 5 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
                </svg>
              </div>
              <div className="bg-[linear-gradient(145deg,#ffffff_0%,#f8fcf9_50%,#edf6f0_100%)] rounded-2xl p-4 sm:p-5 border border-white/90 shadow-[0_4px_16px_rgba(14,72,47,0.06),inset_0_1px_1px_rgba(255,255,255,0.95)] flex items-center justify-between hover:border-emerald-500/40 transition">
                <div>
                  <div className="text-2xl sm:text-[28px] font-black text-[#0a291c] font-sans tracking-tight leading-none">-$340</div>
                  <div className="text-xs font-semibold text-slate-800 mt-1.5">Cloud Bill</div>
                  <div className="text-[11px] text-[#467059]">Monthly average saved</div>
                </div>
                <svg className="w-14 sm:w-16 h-8 text-emerald-500 shrink-0" viewBox="0 0 80 40" fill="none">
                  <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                  <path d="M2 22 Q 20 8, 38 18 T 60 12 T 78 4 L 78 40 L 2 40 Z" fill="currentColor" fillOpacity="0.08" />
                </svg>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:gap-5 w-full">
              <div className="bg-[linear-gradient(145deg,rgba(255,255,255,0.95)_0%,rgba(240,248,243,0.85)_100%)] rounded-xl px-4 py-2.5 border border-white/80 shadow-[0_2px_8px_rgba(14,72,47,0.04),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center gap-2 text-xs font-medium text-[#14422c]">
                <Check size={14} className="text-emerald-600 stroke-[3] shrink-0" />
                <span className="truncate">Automated Code Fixes</span>
              </div>
              <div className="bg-[linear-gradient(145deg,rgba(255,255,255,0.95)_0%,rgba(240,248,243,0.85)_100%)] rounded-xl px-4 py-2.5 border border-white/80 shadow-[0_2px_8px_rgba(14,72,47,0.04),inset_0_1px_0_rgba(255,255,255,0.9)] flex items-center gap-2 text-xs font-medium text-[#14422c]">
                <Check size={14} className="text-emerald-600 stroke-[3] shrink-0" />
                <span className="truncate">Continuous Cost Audits</span>
              </div>
            </div>
          </div>
        </div>

        <div className="h-2" />
      </div>


      {/* ════════════════════════ RIGHT LOGIN CARD PANE ════════════════════════ */}
      <div className="lg:w-1/2 bg-[#fcfdfc] px-6 py-4 sm:py-6 flex items-center justify-center relative h-full overflow-hidden">
        <div className="w-full max-w-[380px] translate-y-2 sm:translate-y-3">

          {/* Main Card */}
          <div className="bg-white rounded-2xl border border-slate-200/90 shadow-lg shadow-slate-900/5 p-5 sm:p-6">

            {/* Header */}
            <div className="text-center mb-3 sm:mb-4">
              <h2 className="text-lg sm:text-[20px] font-bold text-slate-900 tracking-tight">
                {isSignUp ? 'Create an account' : 'Welcome back'}
              </h2>
              <p className="text-xs text-slate-500 mt-0.5">
                {isSignUp ? 'Start optimizing code energy and cloud costs' : 'Please enter your details to sign in'}
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
            <div className="space-y-2 mb-3">

              {/* GitHub OAuth Button */}
              <button
                type="button"
                onClick={handleGitHubQuick}
                disabled={loading || githubLoading || googleLoading}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-full border border-slate-300 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition shadow-2xs cursor-pointer disabled:opacity-50"
              >
                {githubLoading ? (
                  <Loader2 size={14} className="animate-spin text-slate-700" />
                ) : (
                  <Github size={14} className="text-slate-900" />
                )}
                <span>{isSignUp ? 'Sign up with GitHub' : 'Continue with GitHub'}</span>
              </button>

              {/* Google GSI Button */}
              <button
                ref={googleButtonRef}
                type="button"
                onClick={handleGoogleQuick}
                disabled={loading || githubLoading || googleLoading}
                className="w-full flex items-center justify-center gap-2 py-2 px-3 rounded-full border border-slate-300 text-xs font-semibold text-slate-700 bg-white hover:bg-slate-50 transition shadow-2xs cursor-pointer disabled:opacity-50"
              >
                {googleLoading ? (
                  <Loader2 size={14} className="animate-spin text-slate-700" />
                ) : (
                  <svg width="14" height="14" viewBox="0 0 24 24" className="shrink-0">
                    <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.8-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17Z" />
                    <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24Z" />
                    <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.17 0 9.97 0 12s.45 3.83 1.25 5.42l4.03-3.15Z" />
                    <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98Z" />
                  </svg>
                )}
                <span>{isSignUp ? 'Sign up with Google' : 'Continue with Google'}</span>
              </button>

            </div>

            {/* Divider */}
            <div className="relative flex py-0.5 items-center mb-2.5">
              <div className="flex-grow border-t border-slate-200" />
              <span className="shrink-0 mx-3 text-[11px] text-slate-400 font-normal">
                {isSignUp ? 'or register with email' : 'or sign in with email'}
              </span>
              <div className="flex-grow border-t border-slate-200" />
            </div>

            {/* Email/Password Form */}
            <form onSubmit={handleSubmit} className="space-y-2.5">

              {isSignUp && (
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="Sarah Connor"
                    className="w-full px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-slate-800 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition shadow-2xs"
                  />
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  required
                  className="w-full px-3 py-1.5 sm:py-2 text-xs sm:text-sm text-slate-800 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition shadow-2xs"
                />
              </div>

              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-xs font-semibold text-slate-700">Password</label>
                  {!isSignUp && (
                    <button
                      type="button"
                      onClick={() => {
                        setForgotModalOpen(true);
                        setForgotEmail(email);
                        setForgotMessage(null);
                        setReceivedResetToken(null);
                        setResetSuccessMsg(null);
                      }}
                      className="text-[11px] text-slate-500 hover:text-slate-800 transition cursor-pointer"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={passwordOrToken}
                    onChange={(e) => setPasswordOrToken(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full px-3 py-1.5 sm:py-2 pr-9 text-xs sm:text-sm font-mono text-slate-800 bg-white border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600 transition shadow-2xs"
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

              <button
                type="submit"
                disabled={loading || githubLoading || googleLoading}
                className="w-full mt-1 py-2 sm:py-2.5 px-4 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs sm:text-sm font-semibold transition shadow-xs flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
              >
                {loading ? <Loader2 size={15} className="animate-spin text-white" /> : <span>{isSignUp ? 'Create Account' : 'Sign In'}</span>}
              </button>
            </form>

            {/* Sign Up / Sign In Toggle */}
            <div className="text-center mt-3 pt-3 border-t border-slate-100">
              <p className="text-xs text-slate-500 font-normal">
                {isSignUp ? 'Already have an account?' : "Don't have an account?"}{' '}
                <button
                  type="button"
                  onClick={() => { setIsSignUp(!isSignUp); setError(null); }}
                  className="font-semibold text-emerald-800 hover:text-emerald-950 underline underline-offset-2 transition cursor-pointer"
                >
                  {isSignUp ? 'Sign in' : 'Sign up'}
                </button>
              </p>
            </div>
          </div>

          {/* Terms & Privacy */}
          <p className="text-center text-[11px] text-slate-400 mt-3 font-normal leading-relaxed max-w-[340px] mx-auto">
            By continuing, you agree to GreenCode's{' '}
            <button type="button" onClick={() => openLegal('terms')} className="underline hover:text-slate-600 transition cursor-pointer">
              Terms of Service
            </button>{' '}
            and{' '}
            <button type="button" onClick={() => openLegal('privacy')} className="underline hover:text-slate-600 transition cursor-pointer">
              Privacy Policy
            </button>.
          </p>
        </div>
      </div>

      {/* ════════════════════════ FORGOT PASSWORD MODAL ════════════════════════ */}
      {forgotModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full p-6 text-slate-800 relative">
            <button type="button" onClick={() => setForgotModalOpen(false)} className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 cursor-pointer">
              <X size={18} />
            </button>
            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center">
                <KeyRound size={16} />
              </div>
              <h3 className="text-base font-bold text-slate-900">
                {receivedResetToken ? 'Set New Password' : 'Reset Password'}
              </h3>
            </div>

            {resetSuccessMsg ? (
              <div className="py-4 text-center space-y-2">
                <CheckCircle2 size={36} className="text-emerald-600 mx-auto" />
                <p className="text-xs sm:text-sm font-semibold text-slate-900">{resetSuccessMsg}</p>
                <p className="text-[11px] text-slate-500">Redirecting to sign in with your updated credentials...</p>
              </div>
            ) : !receivedResetToken ? (
              <form onSubmit={handleForgotPasswordSubmit} className="space-y-3 mt-3">
                <p className="text-xs text-slate-500 leading-relaxed">
                  Enter your registered email and we'll generate a reset token (sent via email if SMTP is configured, or shown here in dev mode).
                </p>
                {forgotMessage && (
                  <div className="p-2.5 rounded-lg bg-emerald-50 border border-emerald-200 text-xs text-emerald-800">{forgotMessage}</div>
                )}
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">Email address</label>
                  <input
                    type="email"
                    value={forgotEmail}
                    onChange={(e) => setForgotEmail(e.target.value)}
                    required
                    placeholder="name@company.com"
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                  />
                </div>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full py-2 px-3 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {forgotLoading ? <Loader2 size={14} className="animate-spin" /> : 'Send Reset Link'}
                </button>
              </form>
            ) : (
              <form onSubmit={handleResetPasswordSubmit} className="space-y-3 mt-3">
                <p className="text-xs text-emerald-800 bg-emerald-50 p-2.5 rounded-lg border border-emerald-200">
                  Reset token verified. Please enter your new password below.
                </p>
                <div>
                  <label className="block text-xs font-semibold text-slate-700 mb-1">New Password</label>
                  <input
                    type="password"
                    value={newPasswordVal}
                    onChange={(e) => setNewPasswordVal(e.target.value)}
                    required
                    placeholder="Min 6 characters"
                    className="w-full px-3 py-2 text-xs sm:text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                  />
                </div>
                <button
                  type="submit"
                  disabled={forgotLoading}
                  className="w-full py-2 px-3 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
                >
                  {forgotLoading ? <Loader2 size={14} className="animate-spin" /> : 'Update Password & Sign In'}
                </button>
              </form>
            )}
          </div>
        </div>
      )}

      {/* ════════════════════════ GITHUB PAT MODAL ════════════════════════ */}
      {githubPatModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs animate-in fade-in">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-2xl max-w-sm w-full p-6 text-slate-800 relative">
            <button
              type="button"
              onClick={() => {
                setGithubPatModalOpen(false);
                setGithubPatError(null);
              }}
              className="absolute top-4 right-4 text-slate-400 hover:text-slate-700 cursor-pointer"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-2.5 mb-3">
              <div className="w-8 h-8 rounded-lg bg-slate-900 text-white flex items-center justify-center">
                <Github size={18} />
              </div>
              <div>
                <h3 className="text-base font-bold text-slate-900">GitHub Sign In</h3>
                <p className="text-[11px] text-slate-500">Personal Access Token (PAT)</p>
              </div>
            </div>

            <p className="text-xs text-slate-500 mb-3 leading-relaxed">
              Enter your GitHub Personal Access Token (<code className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded text-[11px]">ghp_...</code>) to authenticate directly with your GitHub account.
            </p>

            {githubPatError && (
              <div className="mb-3 p-2.5 rounded-lg bg-rose-50 border border-rose-200 text-xs text-rose-700">
                {githubPatError}
              </div>
            )}

            <form onSubmit={handleGitHubPatSubmit} className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-700 mb-1">
                  GitHub Token
                </label>
                <input
                  type="password"
                  value={githubPatVal}
                  onChange={(e) => setGithubPatVal(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx or demo"
                  required
                  autoFocus
                  className="w-full px-3 py-2 font-mono text-xs border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-600/20 focus:border-emerald-600"
                />
              </div>

              <button
                type="submit"
                disabled={githubPatLoading}
                className="w-full py-2 px-3 rounded-lg bg-[#0e482f] hover:bg-[#0b3824] text-white text-xs font-semibold transition cursor-pointer flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {githubPatLoading ? <Loader2 size={14} className="animate-spin" /> : 'Connect GitHub'}
              </button>
            </form>

            <div className="mt-4 pt-3 border-t border-slate-100 text-[11px] text-slate-500 space-y-1">
              <p>
                Want real OAuth 1-click popup instead? Add <code className="bg-slate-100 px-1 py-0.5 rounded">GITHUB_CLIENT_ID</code> to your <code className="bg-slate-100 px-1 py-0.5 rounded">.env</code>.
              </p>
              <a
                href="https://github.com/settings/developers"
                target="_blank"
                rel="noreferrer"
                className="inline-block text-emerald-800 hover:underline font-medium"
              >
                Create GitHub OAuth App &rarr;
              </a>
            </div>
          </div>
        </div>
      )}

      {/* ════════════════════════ LEGAL MODAL ════════════════════════ */}
      <LegalModal isOpen={legalModalOpen} onClose={() => setLegalModalOpen(false)} initialTab={legalModalTab} />
    </div>
  );
}
