import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Activity, GitBranch, AlertCircle,
  Gauge, Leaf, Zap, DollarSign, Sliders,
  FileText, History, Settings, LogOut, Leaf as LeafIcon,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { gridService } from '../../services/greencodeApi';
import { useEffect, useState } from 'react';
import BrandLogo from '../common/BrandLogo';

interface NavLeaf {
  name: string;
  path: string;
  icon: typeof LayoutDashboard;
  badgeKey?: 'issues';
}

interface NavGroup {
  label: string;
  items: NavLeaf[];
}

/**
 * Enterprise navigation, grouped by job-to-be-done rather than a flat list.
 * A grouped left rail is the clearest visual signal that this is a serious
 * product rather than a toy, and it scales far better than a top navbar as the
 * feature surface grows.
 */
const NAV_GROUPS: NavGroup[] = [
  {
    label: 'Monitor',
    items: [
      { name: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { name: 'Overview', path: '/overview', icon: Activity },
    ],
  },
  {
    label: 'Analyze',
    items: [
      { name: 'Scan Repository', path: '/scan', icon: GitBranch },
      { name: 'Issues', path: '/issues', icon: AlertCircle, badgeKey: 'issues' },
      { name: 'Profiler', path: '/profiler', icon: Zap },
      { name: 'Cloud Carbon', path: '/cloud-carbon', icon: Leaf },
    ],
  },
  {
    label: 'Govern',
    items: [
      { name: 'Budgets', path: '/budgets', icon: DollarSign },
      { name: 'Policies', path: '/policies', icon: Sliders },
      { name: 'Deployments', path: '/deployments', icon: Gauge },
    ],
  },
  {
    label: 'Insights',
    items: [
      { name: 'Reports', path: '/reports', icon: FileText },
      { name: 'History', path: '/history', icon: History },
    ],
  },
];

export default function Sidebar({ issueCount = 0 }: { issueCount?: number }) {
  const { user, logout } = useAuth();
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridIntensity, setGridIntensity] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    gridService
      .getZoneIntensity(zone)
      .then((r) => {
        setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? null);
        setIsLive(r.data.is_live ?? false);
      })
      .catch(() => {
        setGridIntensity(null);
        setIsLive(false);
      });
  }, [zone]);

  const displayName = user?.github_username || user?.username || 'Developer';
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <aside className="hidden lg:flex flex-col w-64 shrink-0 h-screen sticky top-0 bg-white border-r border-zinc-200/80">
      {/* Brand */}
      <div className="h-16 flex items-center gap-2.5 px-5 border-b border-zinc-200/80">
        <BrandLogo size="sm" />
        <div className="flex flex-col leading-none">
          <span className="font-semibold text-[15px] tracking-tight text-zinc-950">GreenCode</span>
          <span className="text-[10px] font-mono text-zinc-400 mt-0.5">SCI Auditor</span>
        </div>
      </div>
      {/* Live grid status chip */}
      <div className="px-3 pt-3">
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-zinc-50 border border-zinc-200/80">
          <span
            className={`w-1.5 h-1.5 rounded-full shrink-0 ${isLive ? 'bg-emerald-500 animate-pulse' : 'bg-zinc-400'}`}
          />
          <span className="text-[10px] font-mono text-zinc-500 truncate flex-1">{zone}</span>
          {gridIntensity !== null && (
            <span className="text-[11px] font-mono font-semibold text-zinc-900 shrink-0">
              {gridIntensity}
              <span className="text-zinc-400 font-normal"> gCO₂/kWh</span>
            </span>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 pb-4 pt-1 space-y-0.5" aria-label="Primary">
        {NAV_GROUPS.map((group) => (
          <div key={group.label}>
            <p className="sidebar-group-label">{group.label}</p>
            <div className="space-y-0.5">
              {group.items.map((item) => {
                const Icon = item.icon;
                const showBadge = item.badgeKey === 'issues' && issueCount > 0;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`
                    }
                  >
                    <Icon size={16} className="shrink-0" />
                    <span className="flex-1 truncate">{item.name}</span>
                    {showBadge && (
                      <span className="badge badge-high shrink-0">{issueCount > 99 ? '99+' : issueCount}</span>
                    )}
                  </NavLink>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* Footer: settings + user */}
      <div className="border-t border-zinc-200/80 p-3 space-y-1">
        <NavLink
          to="/settings"
          className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
        >
          <Settings size={16} className="shrink-0" />
          <span className="flex-1">Settings</span>
        </NavLink>

        <div className="flex items-center gap-2.5 px-2 py-2 mt-1">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="w-8 h-8 rounded-full border border-zinc-200 object-cover shrink-0" />
          ) : (
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-600 to-emerald-800 text-white flex items-center justify-center text-[11px] font-semibold shrink-0">
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-zinc-900 truncate">{displayName}</p>
            <p className="text-[10px] text-zinc-400 truncate flex items-center gap-1">
              <LeafIcon size={9} className="text-emerald-500" />
              {isLive ? 'Live telemetry' : 'Signed in'}
            </p>
          </div>
          <button
            onClick={logout}
            className="shrink-0 text-zinc-400 hover:text-rose-600 transition-colors p-1.5 rounded-md hover:bg-rose-50"
            title="Sign out"
            aria-label="Sign out"
          >
            <LogOut size={15} />
          </button>
        </div>
      </div>
    </aside>
  );
}
