import { Link, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import {
  LayoutDashboard, GitBranch, AlertCircle,
  Gauge, History, Settings, ShieldCheck, Leaf,
  Loader2, LogOut, Github, ChevronDown
} from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAuth } from '../../context/AuthContext';

const NAV_ITEMS = [
  { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
  { name: 'Scan',      path: '/scan',      icon: GitBranch },
  { name: 'Issues',    path: '/issues',    icon: AlertCircle },
  { name: 'Profiler',  path: '/profiler',  icon: Gauge },
  { name: 'History',   path: '/history',   icon: History },
  { name: 'Settings',  path: '/settings',  icon: Settings },
];

export default function Navbar() {
  const location = useLocation();
  const { user, logout } = useAuth();
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [gridIntensity, setGridIntensity] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [gridLoading, setGridLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setGridLoading(true);
    gridService.getZoneIntensity(zone)
      .then((r) => {
        setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? null);
        setIsLive(r.data.is_live ?? false);
      })
      .catch(() => {
        setGridIntensity(null);
        setIsLive(false);
      })
      .finally(() => setGridLoading(false));
  }, [zone]);

  useEffect(() => {
    if (!menuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen]);

  const displayName = user?.github_username || user?.username || 'Developer';
  const avatar = user?.avatar_url;

  return (
    <nav className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">

          <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0 group">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 text-white flex items-center justify-center shadow-sm group-hover:scale-105 transition-transform duration-150">
              <Leaf size={18} className="fill-white/20" />
            </div>
            <div className="leading-tight hidden sm:block">
              <div className="font-extrabold text-sm text-slate-900 tracking-tight">
                <span>GreenCode</span>{' '}
                <span className="text-emerald-600 font-bold">Auditor</span>
              </div>
              <div className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">
                GSF SCI v1.0
              </div>
            </div>
          </Link>

          <div className="hidden md:flex items-center gap-1 bg-slate-100/70 p-1 rounded-xl border border-slate-200/60">
            {NAV_ITEMS.map(({ name, path, icon: Icon }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    active
                      ? 'bg-white text-emerald-800 font-bold shadow-sm border border-slate-200/60'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                  }`}
                >
                  <Icon size={14} className={active ? 'text-emerald-600' : 'text-slate-400'} />
                  {name}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="hidden xl:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200/80 text-xs font-medium text-slate-700">
              {gridLoading ? (
                <Loader2 size={11} className="animate-spin text-slate-400" />
              ) : (
                <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
              )}
              <span className="text-slate-500 font-mono text-[11px]">{zone}</span>
              {gridIntensity !== null && !gridLoading && (
                <span className="font-bold text-slate-900">{gridIntensity} g/kWh</span>
              )}
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/70 text-xs font-bold text-emerald-800">
              <ShieldCheck size={13} className="text-emerald-600" />
              <span>Gate &ge; {threshold}</span>
            </div>

            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((o) => !o)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                className="flex items-center gap-2 pl-1 pr-2 py-1 rounded-full hover:bg-slate-100 transition-colors"
              >
                {avatar ? (
                  <img src={avatar} alt="" className="w-7 h-7 rounded-full border border-slate-200" />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-slate-900 text-white flex items-center justify-center">
                    <Github size={14} />
                  </div>
                )}
                <span className="hidden lg:inline text-xs font-semibold text-slate-700 max-w-[10rem] truncate">
                  {displayName}
                </span>
                <ChevronDown size={13} className={`text-slate-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>

              {menuOpen && (
                <div role="menu" className="absolute right-0 mt-2 w-60 card p-2 shadow-lg z-50 animate-in fade-in">
                  <div className="px-3 py-2.5 border-b border-slate-100">
                    <p className="text-sm font-bold text-slate-900 truncate">{displayName}</p>
                    <p className="text-xs text-slate-500 truncate">{user?.email}</p>
                    {user?.github_token_masked && (
                      <p className="text-[11px] font-mono text-slate-400 mt-1">Token {user.github_token_masked}</p>
                    )}
                  </div>
                  <Link
                    to="/settings"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
                    role="menuitem"
                  >
                    <Settings size={15} className="text-slate-400" />
                    Settings
                  </Link>
                  <button
                    onClick={() => { setMenuOpen(false); logout(); }}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-sm font-medium text-red-600 hover:bg-red-50 transition-colors"
                    role="menuitem"
                  >
                    <LogOut size={15} />
                    Sign out
                  </button>
                </div>
              )}
            </div>
          </div>

        </div>
      </div>
    </nav>
  );
}
