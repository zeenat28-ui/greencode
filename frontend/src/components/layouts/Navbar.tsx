import { Link, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import {
  LayoutDashboard, GitBranch, AlertCircle,
  Gauge, History, Settings, ShieldCheck, Leaf,
  Loader2, LogOut, Github, ChevronDown, Cpu
} from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAuth } from '../../context/AuthContext';

const NAV_ITEMS = [
  { name: 'Dashboard',       path: '/dashboard',     icon: LayoutDashboard },
  { name: 'Scan Code',       path: '/scan',          icon: GitBranch },
  { name: 'Code Issues',     path: '/issues',        icon: AlertCircle },
  { name: 'Cloud & AI',      path: '/cloud-carbon',  icon: Cpu },
  { name: 'Profiler',        path: '/profiler',      icon: Gauge },
  { name: 'Audit History',   path: '/history',       icon: History },
  { name: 'Settings',        path: '/settings',      icon: Settings },
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
    <nav className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50 w-full max-w-full overflow-hidden">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full">
        <div className="flex items-center justify-between h-16 gap-3">

          <Link to="/dashboard" className="flex items-center gap-2.5 shrink-0 group">
            <div className="h-8 w-8 rounded-lg bg-olive-900 text-olive-200 flex items-center justify-center border border-olive-800 shadow-xs group-hover:border-olive-600 transition-colors">
              <Leaf size={16} />
            </div>
            <div className="leading-tight hidden sm:block">
              <div className="font-bold text-sm text-slate-900 tracking-tight flex items-center gap-1.5">
                <span>GreenCode</span>
                <span className="text-[10px] bg-amber-50 text-amber-950 px-2 py-0.5 rounded font-mono border border-amber-300 font-bold">
                  AWS &amp; Alexa+
                </span>
              </div>
              <div className="text-[10px] text-slate-500 font-mono tracking-tight">
                Powered by Amazon Alexa+ &amp; AWS Bedrock
              </div>
            </div>
          </Link>

          <div className="hidden lg:flex items-center gap-1 bg-[#F2F4F3] p-1 rounded-lg border border-slate-200">
            {NAV_ITEMS.map(({ name, path, icon: Icon }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs transition-all duration-150 ${
                    active
                      ? 'bg-olive-900 text-white font-medium shadow-xs border border-olive-950'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/60 font-medium'
                  }`}
                >
                  <Icon size={13} className={active ? 'text-olive-200' : 'text-slate-400'} />
                  {name}
                </Link>
              );
            })}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            {/* Alexa+ & AWS Bedrock Live Indicator */}
            <div className="hidden xl:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-50 border border-amber-200/90 text-xs font-mono font-semibold text-amber-900">
              <span className="w-2 h-2 rounded-full bg-[#FF9900] animate-pulse" />
              <span>Alexa+ &amp; Bedrock MCP</span>
            </div>

            <div className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-slate-50 border border-slate-200 text-xs font-mono text-slate-700">
              {gridLoading ? (
                <Loader2 size={11} className="animate-spin text-slate-400" />
              ) : (
                <span className={`w-2 h-2 rounded-full ${isLive ? 'bg-olive-600 animate-pulse' : 'bg-slate-400'}`} />
              )}
              <span className="text-slate-500 text-[11px]">{zone}</span>
              {gridIntensity !== null && !gridLoading && (
                <span className="font-bold text-slate-900 text-[11px]">{gridIntensity} gCO₂/kWh</span>
              )}
            </div>

            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-olive-50 border border-olive-200 text-xs font-mono font-semibold text-olive-900">
              <ShieldCheck size={13} className="text-olive-700" />
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
