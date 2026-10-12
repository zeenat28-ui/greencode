import { ReactNode, useState } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';
import AmazonTechStackModal from '../common/AmazonTechStackModal';
import { Layers, Github } from 'lucide-react';
import BrandLogo from '../common/BrandLogo';

interface AppLayoutProps {
  children?: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  const [showTechModal, setShowTechModal] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-[#FAFAFA] text-zinc-900 overflow-x-hidden max-w-full">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {children ?? <Outlet />}
      </main>
      <footer className="border-t border-zinc-200/80 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-2 text-xs text-zinc-500">
          <div className="flex items-center gap-2">
            <BrandLogo size="sm" className="w-5 h-5 rounded-md" />
            <span className="font-semibold text-zinc-800">GreenCode v2.1.0</span>
            <span className="text-zinc-300">&middot;</span>
            <span>Polyglot AST, Hardware Energy Telemetry &amp; FinOps Attribution</span>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowTechModal(true)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200/80 text-zinc-700 font-mono text-[11px] font-medium border border-zinc-200/80 transition-colors cursor-pointer"
            >
              <Layers size={12} className="text-emerald-600" />
              Architecture &amp; Specs
            </button>
            <a
              href="https://github.com/zeenat28-ui/greencode"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-zinc-500 hover:text-zinc-900 font-mono text-[11px] transition-colors"
            >
              <Github size={12} />
              <span>Apache-2.0</span>
            </a>
          </div>
        </div>
      </footer>
      <AmazonTechStackModal isOpen={showTechModal} onClose={() => setShowTechModal(false)} />
    </div>
  );
}
