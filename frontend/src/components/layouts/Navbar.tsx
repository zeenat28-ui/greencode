import { Link, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import {
  LayoutDashboard, GitBranch, AlertCircle,
  Gauge, Settings, ShieldCheck,
  Loader2, LogOut, Github, ChevronDown,
  Sliders, DollarSign, Activity, FileText
} from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAuth } from '../../context/AuthContext';
import BrandLogo from '../common/BrandLogo';

const NAV_ITEMS = [
  { name: 'Dashboard',   path: '/dashboard',   icon: LayoutDashboard },
  { name: 'Scan',        path: '/scan',        icon: GitBranch },
  { name: 'Issues',      path: '/issues',      icon: AlertCircle },
  { name: 'Overview',    path: '/overview',    icon: Activity },
  { name: 'Budgets',     path: '/budgets',     icon: DollarSign },
  { name: 'Policies',    path: '/policies',    icon: Sliders },
  { name: 'Deploys',     path: '/deployments', icon: Gauge },
  { name: 'Reports',     path: '/reports',     icon: FileText },
  { name: 'Settings',    path: '/settings',    icon: Settings },
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
    <nav className="bg-white/95 backdrop-blur-md border-b border-zinc-200/80 sticky top-0 z-50 w-full">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="flex items-center justify-between h-14 gap-3">

          <Link to="/dashboard" className="flex items-center gap-2 shrink-0 group">
            <BrandLogo size="sm" />
            <span className="font-semibold text-sm text-zinc-950 tracking-tight whitespace-nowrap">
              GreenCode
            </span>
            <span className="hidden sm:inline-block text-[10px] bg-zinc-100 text-zinc-600 px-1.5 py-0.5 rounded font-mono border border-zinc-200/80 font-medium whitespace-nowrap">
              v2.1
            </span>
          </Link>

          <div className="hidden lg:flex items-center gap-0.5 bg-zinc-100/80 p-1 rounded-lg border border-zinc-200/70 overflow-x-auto">
            {NAV_ITEMS.map(({ name, path, icon: Icon }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs whitespace-nowrap transition-all duration-150 ${
                    active
                      ? 'bg-zinc-900 text-white font-medium shadow-sm'
                      : 'text-zinc-600 hover:text-zinc-950 hover:bg-white/70 font-medium'
                  }`}
                >
                  <Icon size={13} className={active ? 'text-emerald-400' : 'text-zinc-400'} />
                  <span>{name}</span>
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-zinc-50 border border-zinc-200/80 text-xs font-mono text-zinc-700 whitespace-nowrap">
              {gridLoading ? (
                <Loader2 size={11} className="animate-spin text-zinc-400" />
              ) : (
                <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
              )}
              <span className="text-zinc-500 text-[11px]">{zone}</span>
              {gridIntensity !== null && !gridLoading && (
                <span className="font-semibold text-zinc-900 text-[11px]">{gridIntensity} gCO₂/kWh</span>
              )}
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-emerald-50/80 border border-emerald-200/80 text-xs font-mono font-medium text-emerald-900 whitespace-nowrap">
              <ShieldCheck size={13} className="text-emerald-600" />
              <span>Gate &ge; {threshold}</span>
            </div>

            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setMenuOpen((o) => !o)}
                aria-haspopup="menu"
                aria-expanded={menuOpen}
                className="flex items-center gap-1.5 pl-1 pr-2 py-1 rounded-full hover:bg-zinc-100 transition-colors border border-transparent hover:border-zinc-200"
              >
                {avatar ? (
                  <img src={avatar} alt="" className="w-7 h-7 rounded-full border border-zinc-200 object-cover" />
                ) : (
                  <div className="w-7 h-7 rounded-full bg-zinc-900 text-white flex items-center justify-center">
                    <Github size={14} />
                  </div>
                )}
                <span className="hidden md:inline text-xs font-medium text-zinc-700 max-w-[7.5rem] truncate">
                  {displayName}
                </span>
                <ChevronDown size={13} className={`text-zinc-400 transition-transform ${menuOpen ? 'rotate-180' : ''}`} />
              </button>

              {menuOpen && (
                <div role="menu" className="absolute right-0 mt-2 w-60 card p-2 shadow-lg z-50">
                  <div className="px-3 py-2.5 border-b border-zinc-100">
                    <p className="text-xs font-semibold text-zinc-900 truncate">{displayName}</p>
                    <p className="text-[11px] text-zinc-500 truncate">{user?.email}</p>
                    {user?.github_token_masked && (
                      <p className="text-[11px] font-mono text-zinc-400 mt-1">Token {user.github_token_masked}</p>
                    )}
                  </div>
                  <Link
                    to="/settings"
                    onClick={() => setMenuOpen(false)}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-xs font-medium text-zinc-700 hover:bg-zinc-50 transition-colors mt-1"
                    role="menuitem"
                  >
                    <Settings size={14} className="text-zinc-400" />
                    Settings
                  </Link>
                  <button
                    onClick={() => { setMenuOpen(false); logout(); }}
                    className="flex items-center gap-2.5 w-full px-3 py-2 rounded-lg text-xs font-medium text-red-600 hover:bg-red-50 transition-colors"
                    role="menuitem"
                  >
                    <LogOut size={14} />
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
