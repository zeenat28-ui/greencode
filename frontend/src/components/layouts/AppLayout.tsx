import { useEffect, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import Sidebar from './Sidebar';
import AmazonTechStackModal from '../common/AmazonTechStackModal';
import ErrorBoundary from '../common/ErrorBoundary';
import { Layers, Github } from 'lucide-react';
import { useT } from '../../i18n/I18nContext';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { ScanResult } from '../../types';

export default function AppLayout() {
  const t = useT();
  const [showTechModal, setShowTechModal] = useState(false);
  const [navOpen, setNavOpen] = useState(false);
  const [scanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const issueCount = scanData?.total_violations ?? 0;

  useEffect(() => {
    if (!navOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setNavOpen(false);
    };
    document.addEventListener('keydown', onKey);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = '';
    };
  }, [navOpen]);

  return (
    <div className="h-[100dvh] flex bg-[var(--gc-bg-canvas)] text-[var(--gc-text-primary)] overflow-hidden">
      <div className="hidden lg:block shrink-0">
        <Sidebar issueCount={issueCount} />
      </div>

      {navOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <button
            type="button"
            className="absolute inset-0 bg-black/50"
            aria-label={t('nav.closeMenu')}
            onClick={() => setNavOpen(false)}
          />
          <div className="relative z-10 h-full">
            <Sidebar issueCount={issueCount} onNavigate={() => setNavOpen(false)} />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0 min-h-0">
        <Navbar navOpen={navOpen} onToggleNav={() => setNavOpen((v) => !v)} />
        <main className="flex-1 overflow-auto px-4 py-3 lg:px-5">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </main>
        <footer className="shrink-0 border-t border-[var(--gc-border-default)] bg-[var(--gc-rail)] px-4 py-1.5 flex items-center justify-between gap-3 text-[11px] text-[var(--gc-text-tertiary)]">
          <span className="font-medium text-[var(--gc-text-secondary)] truncate">
            {t('footer.product', { version: t('app.versionFull') })}
            <span className="hidden sm:inline"> · {t('footer.blurb')}</span>
          </span>
          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={() => setShowTechModal(true)}
              className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-[var(--gc-border-default)] hover:bg-[var(--gc-bg-subtle)] text-[var(--gc-text-secondary)] font-mono"
            >
              <Layers size={11} />
              {t('footer.architecture')}
            </button>
            <a
              href="https://github.com/zeenat28-ui/greencode"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 hover:text-[var(--gc-text-primary)] font-mono"
            >
              <Github size={11} />
              {t('footer.license')}
            </a>
          </div>
        </footer>
      </div>
      <AmazonTechStackModal isOpen={showTechModal} onClose={() => setShowTechModal(false)} />
    </div>
  );
}
