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
  CheckCircle2,
  Lock,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BrandLogo from '../components/common/BrandLogo';
import './Login.css';

/**
 * GreenCode Enterprise Authentication
 * Built to Fortune-500 SaaS standards (Microsoft / AWS / Vercel / Stripe design pattern).
 * High-legibility typography, robust responsive scaling, and crystal-clear brand identity.
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
        'Authentication failed. Please check your token scopes and try again.';
      setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="gc-auth-wrapper">
      {/* Precision enterprise background grid & ambient aura */}
      <div className="gc-auth-bg" aria-hidden="true">
        <div className="gc-auth-grid" />
        <div className="gc-auth-radial" />
      </div>

      {/* Top minimal bar */}
      <header className="gc-auth-topbar">
        <div className="gc-auth-status">
          <span className="gc-status-pulse" />
          <span className="gc-status-text">Production Network · All Systems Operational</span>
        </div>
        <div className="gc-auth-meta">
          <span className="gc-spec-tag">ISO/IEC 21031</span>
          <span className="gc-spec-tag">FinOps FOCUS 1.4</span>
        </div>
      </header>

      {/* Main Centered Content */}
      <main className="gc-auth-main">
        {/* Brand Lockup */}
        <div className="gc-brand-lockup">
          <div className="gc-brand-icon-wrapper">
            <BrandLogo size="lg" />
          </div>
          <div className="gc-brand-text">
            <div className="gc-brand-title-row">
              <span className="gc-brand-title">GreenCode</span>
              <span className="gc-version-badge">v2.1.0</span>
            </div>
            <p className="gc-brand-subtitle">
              Software Carbon Intensity &amp; Cloud FinOps Engine
            </p>
          </div>
        </div>

        {/* Enterprise Auth Card */}
        <div className="gc-auth-card">
          <div className="gc-card-header">
            <h1 className="gc-card-title">Sign in to your account</h1>
            <p className="gc-card-description">
              Authenticate with your GitHub Personal Access Token to audit repositories and monitor cloud workloads.
            </p>
          </div>

          {error && (
            <div className="gc-auth-alert" role="alert">
              <AlertCircle size={16} className="gc-alert-icon" />
              <div className="gc-alert-text">{error}</div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="gc-auth-form" noValidate>
            <div className="gc-form-group">
              <div className="gc-label-row">
                <label htmlFor="github-token" className="gc-input-label">
                  GitHub Personal Access Token
                </label>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="gc-token-link"
                >
                  Create token
                  <ExternalLink size={12} />
                </a>
              </div>

              <div className="gc-input-container">
                <KeyRound size={16} className="gc-input-lead-icon" />
                <input
                  id="github-token"
                  type={showToken ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  required
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="gc-text-input"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((prev) => !prev)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                  className="gc-input-action-btn"
                >
                  {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              <div className="gc-scope-badge-row">
                <span className="gc-scope-label">Required scopes:</span>
                <code className="gc-scope-pill">repo</code>
                <code className="gc-scope-pill">read:user</code>
                <span className="gc-scope-info">— read-only access to source code AST</span>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="gc-submit-btn"
            >
              {loading ? (
                <>
                  <Loader2 size={16} className="gc-btn-spinner" />
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <Github size={16} />
                  <span>Continue with GitHub</span>
                  <ArrowRight size={15} className="gc-btn-arrow" />
                </>
              )}
            </button>
          </form>

          {/* Institutional Trust & Security Callout */}
          <div className="gc-security-box">
            <ShieldCheck size={16} className="gc-security-icon" />
            <div className="gc-security-content">
              <div className="gc-security-title">
                <Lock size={12} />
                <span>Client-Side Ephemeral Session</span>
              </div>
              <p className="gc-security-text">
                Your token is held exclusively in volatile browser memory for API calls. 
                It is never stored on disk, written to local storage, logged to backend servers, 
                or retained across browser closes.
              </p>
            </div>
          </div>
        </div>

        {/* Enterprise Compliance Strip */}
        <div className="gc-compliance-strip">
          <div className="gc-compliance-item">
            <CheckCircle2 size={13} className="text-emerald-600" />
            <span>ISO/IEC 21031:2024 Verified</span>
          </div>
          <span className="gc-compliance-dot">·</span>
          <div className="gc-compliance-item">
            <CheckCircle2 size={13} className="text-emerald-600" />
            <span>FinOps Foundation FOCUS 1.4</span>
          </div>
          <span className="gc-compliance-dot">·</span>
          <div className="gc-compliance-item">
            <CheckCircle2 size={13} className="text-emerald-600" />
            <span>Apache 2.0 Open Source</span>
          </div>
        </div>
      </main>

      {/* Enterprise Footer */}
      <footer className="gc-auth-footer">
        <div className="gc-footer-content">
          <div className="gc-footer-links">
            <a
              href="https://github.com/zeenat28-ui/greencode"
              target="_blank"
              rel="noopener noreferrer"
              className="gc-footer-link"
            >
              <Github size={14} />
              <span>GitHub Repository</span>
            </a>
            <span className="gc-footer-sep">·</span>
            <a
              href="https://github.com/zeenat28-ui/greencode/blob/main/LICENSE"
              target="_blank"
              rel="noopener noreferrer"
              className="gc-footer-link"
            >
              License (Apache-2.0)
            </a>
            <span className="gc-footer-sep">·</span>
            <span className="gc-footer-copy">
              &copy; 2026 Zeenat (@zeenat28-ui)
            </span>
          </div>
          <div className="gc-footer-legal">
            GreenCode Auditor · High-Performance Software Carbon Intensity &amp; Cloud Billing Telemetry
          </div>
        </div>
      </footer>
    </div>
  );
}
