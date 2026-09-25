import { Link, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import {
  LayoutDashboard, GitBranch, AlertCircle,
  Gauge, History, Settings, ShieldCheck, Zap,
  Loader2, Leaf
} from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';

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
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [gridIntensity, setGridIntensity] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [gridLoading, setGridLoading] = useState(true);

  useEffect(() => {
    setGridLoading(true);
    gridService.getZoneIntensity(zone)
      .then(r => {
        setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? null);
        setIsLive(r.data.is_live ?? false);
      })
      .catch(() => {
        setGridIntensity(null);
        setIsLive(false);
      })
      .finally(() => {
        setGridLoading(false);
      });
  }, [zone]);

  return (
    <nav className="bg-white/95 backdrop-blur-md border-b border-slate-200/80 sticky top-0 z-50 shadow-2xs">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">

          {/* Brand */}
          <Link to="/dashboard" className="flex items-center gap-3 shrink-0 group">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-700 text-white flex items-center justify-center shadow-xs shadow-emerald-500/20 group-hover:scale-105 transition-transform duration-150">
              <Leaf size={18} className="fill-white/20 text-white" />
            </div>
            <div className="leading-tight">
              <div className="font-extrabold text-sm text-slate-900 tracking-tight flex items-center gap-1.5">
                <span>GreenCode</span>
                <span className="text-emerald-600 font-bold">Auditor</span>
              </div>
              <div className="text-[10px] text-slate-400 font-semibold tracking-wider uppercase">
                GSF SCI v1.0 &middot; ISO/IEC 21031
              </div>
            </div>
          </Link>

          {/* Desktop Nav links */}
          <div className="hidden md:flex items-center gap-1 bg-slate-100/70 p-1 rounded-xl border border-slate-200/60">
            {NAV_ITEMS.map(({ name, path, icon: Icon }) => {
              const active = location.pathname === path;
              return (
                <Link
                  key={path}
                  to={path}
                  className={`flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 ${
                    active
                      ? 'bg-white text-emerald-800 font-bold shadow-xs border border-slate-200/60'
                      : 'text-slate-600 hover:text-slate-900 hover:bg-white/60'
                  }`}
                >
                  <Icon size={14} className={active ? 'text-emerald-600' : 'text-slate-400'} />
                  {name}
                </Link>
              );
            })}
          </div>

          {/* Status pills */}
          <div className="flex items-center gap-2">
            {/* Live grid telemetry pill */}
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-50 border border-slate-200/80 text-xs font-medium text-slate-700 shadow-2xs">
              {gridLoading ? (
                <>
                  <Loader2 size={11} className="animate-spin text-slate-400" />
                  <span className="text-slate-400 font-mono text-[11px]">{zone}</span>
                </>
              ) : (
                <>
                  <span
                    className={`w-2 h-2 rounded-full ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`}
                  />
                  <span className="text-slate-500 font-mono text-[11px]">{zone}</span>
                  {gridIntensity !== null && (
                    <span className="font-bold text-slate-900">{gridIntensity} g/kWh</span>
                  )}
                </>
              )}
            </div>

            {/* Quality gate threshold pill */}
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-emerald-50 border border-emerald-200/70 text-xs font-bold text-emerald-800 shadow-2xs">
              <ShieldCheck size={13} className="text-emerald-600" />
              <span>Gate &ge; {threshold}</span>
            </div>

            {/* IBM Bob 2.0 Engine badge */}
            <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl bg-blue-50/90 border border-blue-200/70 text-blue-700 text-xs font-bold shadow-2xs">
              <Zap size={12} className="fill-blue-500 text-blue-500" />
              <span>IBM Bob 2.0</span>
            </div>
          </div>

        </div>
      </div>
    </nav>
  );
}

