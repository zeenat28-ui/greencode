import { useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import AmazonTechStackModal from '../common/AmazonTechStackModal';
import AlexaAssistant from '../common/AlexaAssistant';
import ErrorBoundary from '../common/ErrorBoundary';
import { Github, Layers } from 'lucide-react';
import { useT } from '../../i18n/I18nContext';

export default function AppLayout() {
  const t = useT();
  const [showTechModal, setShowTechModal] = useState(false);

  return (
    <div className="gc-console-shell h-[100dvh] flex flex-col text-[var(--gc-text-primary)] overflow-hidden">
      <Navbar />
      <main className="gc-console-main flex-1 overflow-auto px-4 py-3 lg:px-5">
        <div className="mx-auto w-full max-w-[1600px]">
          <ErrorBoundary>
            <Outlet />
          </ErrorBoundary>
        </div>
      </main>
      <footer className="gc-console-footer shrink-0 px-4 py-1.5 flex items-center justify-between gap-3 text-[11px]">
        <span className="font-medium truncate">
          <span className="gc-live-dot" /> {t('footer.product', { version: t('app.versionFull') })}
          <span className="hidden sm:inline"> · {t('footer.blurb')}</span>
        </span>
        <div className="flex items-center gap-2 shrink-0">
          <button
            type="button"
            onClick={() => setShowTechModal(true)}
            className="gc-toolbar-link inline-flex items-center gap-1 px-2 py-0.5"
          >
            <Layers size={11} />
            {t('footer.architecture')}
          </button>
          <a
            href="https://github.com/zeenat28-ui/greencode"
            target="_blank"
            rel="noopener noreferrer"
            className="gc-toolbar-link inline-flex items-center gap-1 font-mono"
          >
            <Github size={11} />
            {t('footer.license')}
          </a>
        </div>
      </footer>
      <AlexaAssistant />
      <AmazonTechStackModal isOpen={showTechModal} onClose={() => setShowTechModal(false)} />
    </div>
  );
}
