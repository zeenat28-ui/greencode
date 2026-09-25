import { ReactNode } from 'react';
import Navbar from './Navbar';

interface AppLayoutProps {
  children: ReactNode;
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-7">
        {children}
      </main>
      <footer className="border-t border-slate-200 bg-white mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3 flex items-center justify-between">
          <span className="text-xs text-slate-400">
            GreenCode Auditor &mdash; ISO/IEC 21031:2024 &middot; GSF SCI v1.0
          </span>
          <span className="text-xs text-slate-400">
            Powered by IBM Bob 2.0
          </span>
        </div>
      </footer>
    </div>
  );
}
