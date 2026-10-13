import { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RotateCcw, RefreshCw } from 'lucide-react';

interface ErrorBoundaryProps {
  children: ReactNode;
  /** Optional label shown in the fallback header, e.g. the current page name. */
  scope?: string;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

/**
 * Route/section-level error boundary.
 *
 * Without this, any render error inside a page crashes the entire tree into a
 * blank white screen. This catches it and renders a recoverable fallback with a
 * retry action, so a single broken widget never takes down the whole app.
 */
export default class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Central place to forward to an error tracker (Sentry, etc.) later.
    // eslint-disable-next-line no-console
    console.error('[ErrorBoundary]', this.props.scope || 'app', error, info.componentStack);
  }

  private handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    return (
      <div className="min-h-[60vh] flex items-center justify-center p-6">
        <div className="card-elevated max-w-md w-full p-8 text-center animate-fade-in">
          <div className="w-12 h-12 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center text-rose-600 mx-auto mb-4">
            <AlertTriangle size={22} />
          </div>
          <h2 className="text-base font-semibold text-zinc-900 mb-1">
            {this.props.scope ? `${this.props.scope} hit an error` : 'Something went wrong'}
          </h2>
          <p className="text-xs text-zinc-500 mb-5 leading-relaxed">
            An unexpected error occurred while rendering this view. You can retry, or reload the
            page if the problem persists.
          </p>
          {this.state.error?.message && (
            <pre className="text-[11px] font-mono text-left text-rose-700 bg-rose-50/60 border border-rose-200/80 rounded-lg p-3 mb-5 overflow-x-auto max-w-full whitespace-pre-wrap break-words">
              {this.state.error.message}
            </pre>
          )}
          <div className="flex items-center justify-center gap-2">
            <button onClick={this.handleReset} className="btn-secondary text-xs">
              <RotateCcw size={13} /> Try again
            </button>
            <button onClick={() => window.location.reload()} className="btn-dark text-xs">
              <RefreshCw size={13} /> Reload
            </button>
          </div>
        </div>
      </div>
    );
  }
}
