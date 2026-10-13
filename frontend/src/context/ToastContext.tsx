import { createContext, useCallback, useContext, useMemo, useRef, useState, ReactNode } from 'react';
import { CheckCircle2, AlertCircle, Info, X, AlertTriangle } from 'lucide-react';

export type ToastKind = 'success' | 'error' | 'info' | 'warning';

interface Toast {
  id: number;
  kind: ToastKind;
  message: string;
}

interface ToastContextValue {
  toast: (message: string, kind?: ToastKind) => void;
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

const KIND_STYLES: Record<ToastKind, { wrap: string; icon: ReactNode }> = {
  success: {
    wrap: 'bg-white border-emerald-200 text-zinc-900',
    icon: <CheckCircle2 size={16} className="text-emerald-600" />,
  },
  error: {
    wrap: 'bg-white border-rose-200 text-zinc-900',
    icon: <AlertCircle size={16} className="text-rose-600" />,
  },
  warning: {
    wrap: 'bg-white border-amber-200 text-zinc-900',
    icon: <AlertTriangle size={16} className="text-amber-600" />,
  },
  info: {
    wrap: 'bg-white border-zinc-200 text-zinc-900',
    icon: <Info size={16} className="text-zinc-500" />,
  },
};

const AUTO_DISMISS_MS = 4500;

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const idRef = useRef(0);
  const timers = useRef<Map<number, number>>(new Map());

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const toast = useCallback(
    (message: string, kind: ToastKind = 'info') => {
      const id = ++idRef.current;
      setToasts((prev) => [...prev.slice(-3), { id, kind, message }]);
      const timer = window.setTimeout(() => dismiss(id), AUTO_DISMISS_MS);
      timers.current.set(id, timer);
    },
    [dismiss],
  );

  const value = useMemo<ToastContextValue>(
    () => ({
      toast,
      success: (m) => toast(m, 'success'),
      error: (m) => toast(m, 'error'),
      info: (m) => toast(m, 'info'),
      warning: (m) => toast(m, 'warning'),
    }),
    [toast],
  );

  return (
    <ToastContext.Provider value={value}>
      {children}
      {/* Live region: screen readers announce new toasts automatically. */}
      <div
        className="fixed bottom-5 right-5 z-[100] flex flex-col gap-2 w-[min(92vw,22rem)]"
        role="region"
        aria-live="polite"
        aria-label="Notifications"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            className={`flex items-start gap-2.5 p-3 rounded-xl border shadow-lg animate-fade-in ${KIND_STYLES[t.kind].wrap}`}
          >
            <span className="shrink-0 mt-0.5">{KIND_STYLES[t.kind].icon}</span>
            <p className="text-xs leading-relaxed flex-1 text-zinc-700">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="shrink-0 text-zinc-400 hover:text-zinc-700 transition-colors"
              aria-label="Dismiss notification"
            >
              <X size={14} />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error('useToast must be used within a ToastProvider');
  return ctx;
}
