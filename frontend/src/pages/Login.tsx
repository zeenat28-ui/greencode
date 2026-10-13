import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Login.css';
import {
  Github,
  KeyRound,
  ArrowRight,
  Loader2,
  AlertCircle,
  Eye,
  EyeOff,
  ExternalLink,
  Shield,
  Zap,
  BarChart3,
  Leaf,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import BrandLogo from '../components/common/BrandLogo';

/**
 * Enterprise Split-Screen Login
 * Left  → Rich branded panel with features & visuals
 * Right → Clean authentication form
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
    <div className="login-root">
      {/* ═══════════════ LEFT PANEL — Branding & Features ═══════════════ */}
      <div className="login-left">
        {/* Animated background elements */}
        <div className="login-left-bg">
          <div className="login-orb login-orb-1" />
          <div className="login-orb login-orb-2" />
          <div className="login-orb login-orb-3" />
          <div className="login-grid-overlay" />
        </div>

        <div className="login-left-content">
          {/* Logo & Brand */}
          <div className="login-brand">
            <div className="login-logo-box">
              <BrandLogo size="lg" />
            </div>
            <div>
              <h1 className="login-brand-name">GreenCode</h1>
              <span className="login-version-badge">v2.1.0</span>
            </div>
          </div>

          {/* Tagline */}
          <div className="login-tagline">
            <h2 className="login-headline">
              Measure. Optimize.<br />
              <span className="login-headline-accent">Decarbonize.</span>
            </h2>
            <p className="login-subtext">
              The enterprise platform for software carbon intensity analysis, 
              cloud FinOps cost attribution, and sustainability compliance.
            </p>
          </div>

          {/* Feature Pills */}
          <div className="login-features">
            <div className="login-feature-item">
              <div className="login-feature-icon">
                <BarChart3 size={18} />
              </div>
              <div>
                <div className="login-feature-title">Carbon Analytics</div>
                <div className="login-feature-desc">Real-time SCI scoring per ISO/IEC 21031:2024</div>
              </div>
            </div>
            <div className="login-feature-item">
              <div className="login-feature-icon">
                <Zap size={18} />
              </div>
              <div>
                <div className="login-feature-title">FinOps Attribution</div>
                <div className="login-feature-desc">FOCUS 1.4 compliant cost & energy tracking</div>
              </div>
            </div>
            <div className="login-feature-item">
              <div className="login-feature-icon">
                <Leaf size={18} />
              </div>
              <div>
                <div className="login-feature-title">Polyglot AST Analysis</div>
                <div className="login-feature-desc">Deep code scanning across 20+ languages</div>
              </div>
            </div>
          </div>

          {/* Trust strip */}
          <div className="login-trust">
            <span>ISO/IEC 21031:2024</span>
            <span className="login-trust-dot">·</span>
            <span>FinOps FOCUS 1.4</span>
            <span className="login-trust-dot">·</span>
            <span>Apache-2.0</span>
          </div>
        </div>
      </div>

      {/* ═══════════════ RIGHT PANEL — Auth Form ═══════════════ */}
      <div className="login-right">
        <div className="login-form-wrapper">
          {/* Mobile-only brand (hidden on desktop) */}
          <div className="login-mobile-brand">
            <div className="login-logo-box-sm">
              <BrandLogo size="md" />
            </div>
            <span className="login-brand-name-sm">GreenCode</span>
          </div>

          <div className="login-form-header">
            <h2 className="login-form-title">Sign in to your account</h2>
            <p className="login-form-subtitle">
              Enter your GitHub Personal Access Token to get started with repository auditing.
            </p>
          </div>

          {error && (
            <div className="login-error" role="alert">
              <AlertCircle size={16} />
              <span>{error}</span>
            </div>
          )}

          <form onSubmit={handleSubmit} className="login-form" noValidate>
            <div className="login-field">
              <div className="login-label-row">
                <label htmlFor="github-token" className="login-label">
                  GitHub Personal Access Token
                </label>
                <a
                  href="https://github.com/settings/tokens/new?scopes=repo,read:user&description=GreenCode-Auditor"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="login-create-link"
                >
                  Create token
                  <ExternalLink size={12} />
                </a>
              </div>

              <div className="login-input-wrapper">
                <KeyRound size={16} className="login-input-icon" />
                <input
                  id="github-token"
                  type={showToken ? 'text' : 'password'}
                  autoComplete="off"
                  spellCheck={false}
                  required
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
                  className="login-input"
                />
                <button
                  type="button"
                  onClick={() => setShowToken((s) => !s)}
                  aria-label={showToken ? 'Hide token' : 'Show token'}
                  className="login-eye-btn"
                >
                  {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>

              <p className="login-hint">
                Requires <code>repo</code> and <code>read:user</code> scopes to analyze code.
              </p>
            </div>

            <button type="submit" disabled={loading} className="login-submit">
              {loading ? (
                <>
                  <Loader2 size={18} className="animate-spin" />
                  <span>Verifying credentials...</span>
                </>
              ) : (
                <>
                  <Github size={18} />
                  <span>Continue with GitHub</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          </form>

          {/* Security note */}
          <div className="login-security-note">
            <Shield size={14} />
            <span>
              <strong>Ephemeral Session</strong> — Your token is retained only in browser memory. 
              Never saved to disk, database, or server logs.
            </span>
          </div>

          {/* Footer */}
          <div className="login-footer">
            <a
              href="https://github.com/zeenat28-ui/greencode"
              target="_blank"
              rel="noopener noreferrer"
              className="login-footer-link"
            >
              <Github size={13} />
              Source Repository
            </a>
            <span className="login-footer-dot">·</span>
            <span>© 2026 Zeenat (@zeenat28-ui)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
