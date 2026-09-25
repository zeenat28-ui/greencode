import { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Eye, EyeOff, Loader2 } from 'lucide-react';
import { theme } from '../styles/theme';

const loginSchema = z.object({
  login: z.string().min(1, 'Email or username is required'),
  password: z.string().min(1, 'Password is required'),
});

type LoginFormData = z.infer<typeof loginSchema>;

export default function Login() {
  const navigate = useNavigate();
  const location = useLocation();
  const { login, githubSignin } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ghToken, setGhToken] = useState('');
  const [useGithub, setUseGithub] = useState(false);

  const { register, handleSubmit, formState: { errors } } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
  });

  const from = location.state?.from?.pathname || '/dashboard';

  const onSubmit = async (data: LoginFormData) => {
    if (useGithub && ghToken) {
      setIsSubmitting(true);
      try {
        await githubSignin(ghToken);
        navigate(from, { replace: true });
      } catch (err: any) {
        setError(err.response?.data?.detail || 'GitHub authentication failed');
      } finally {
        setIsSubmitting(false);
      }
      return;
    }
    setIsSubmitting(true);
    try {
      await login(data.login, data.password);
      navigate(from, { replace: true });
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid credentials. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-mint-50">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="flex items-center justify-center gap-3 mb-4">
            <img src="/logo.png" alt="GreenCode" className="h-12 w-12 rounded-full" />
            <span className="font-black text-2xl text-mint-800" style={{ color: theme.colors.primary }}>GreenCode Auditor</span>
          </div>
          <h1 className="text-2xl font-bold text-slate-800">Welcome back</h1>
          <p className="text-slate-500 mt-1">Sign in to your account to continue</p>
        </div>

        <div className="bg-white rounded-xl border border-mint-200 shadow-lg p-8">
          <div className="flex gap-2 mb-6">
            <button
              type="button"
              onClick={() => { setUseGithub(false); setError(null); }}
              className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
                !useGithub ? 'bg-mint-600 text-white shadow-md' : 'bg-slate-100 text-slate-600'
              }`}
            >
              Email / Username
            </button>
            <button
              type="button"
              onClick={() => { setUseGithub(true); setError(null); }}
              className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
                useGithub ? 'bg-mint-600 text-white shadow-md' : 'bg-slate-100 text-slate-600'
              }`}
            >
              GitHub Token
            </button>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-4">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {!useGithub ? (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Email or Username
                </label>
                <input
                  type="text"
                  placeholder="you@example.com or your_username"
                  className="input"
                  {...register('login')}
                />
                {errors.login && <p className="text-xs text-red-600 mt-1">{errors.login.message}</p>}
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    className="input pr-12"
                    {...register('password')}
                  />
                  <button
                    type="button"
                    tabIndex={-1}
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                {errors.password && <p className="text-xs text-red-600 mt-1">{errors.password.message}</p>}
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Signing in...
                  </>
                ) : (
                  'Sign In'
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1.5">
                  GitHub Personal Access Token
                </label>
                <input
                  type="password"
                  placeholder="ghp_... or github_pat_..."
                  className="input"
                  value={ghToken}
                  onChange={(e) => setGhToken(e.target.value)}
                />
                <p className="text-xs text-slate-500 mt-1">
                  Token needs 'repo' scope. Generate at{' '}
                  <a
                    href="https://github.com/settings/tokens"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="underline"
                    style={{ color: theme.colors.primary }}
                  >
                    github.com/settings/tokens
                  </a>
                </p>
              </div>

              <button
                type="submit"
                disabled={isSubmitting || !ghToken}
                className="w-full btn-primary flex items-center justify-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" /> Connecting...
                  </>
                ) : (
                  'Connect with GitHub'
                )}
              </button>
            </form>
          )}

          {!useGithub && (
            <div className="mt-6 text-center text-sm">
              <span className="text-slate-500">Need an account? </span>
              <button
                onClick={() => navigate('/signup')}
                className="font-semibold hover:underline"
                style={{ color: theme.colors.primary }}
              >
                Create Account
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
