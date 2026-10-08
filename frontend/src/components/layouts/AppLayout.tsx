import { ReactNode } from 'react';
import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

interface AppLayoutProps {
  children?: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col w-full max-w-full overflow-x-hidden">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-7 overflow-x-hidden">
        {children ?? <Outlet />}
      </main>
      <footer className="border-t border-slate-200/80 bg-white mt-auto w-full max-w-full overflow-x-hidden">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-wrap items-center justify-between gap-3 text-xs text-slate-500 font-mono">
          <span>
            GreenCode &mdash; ISO/IEC 21031 &middot; GSF SCI v1.0
          </span>
          <span className="flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-olive-600" />
            <span>Amazon Bedrock &amp; Alexa MCP Integration</span>
          </span>
        </div>
      </footer>
    </div>
  );
}
