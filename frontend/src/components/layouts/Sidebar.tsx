import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard, Activity, GitBranch, AlertCircle,
  Gauge, Leaf, Zap, DollarSign, Sliders,
  FileText, History, Settings, LogOut,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { gridService } from '../../services/greencodeApi';
import { useEffect, useState } from 'react';
import BrandLogo from '../common/BrandLogo';
import { useT } from '../../i18n/I18nContext';

interface NavLeaf {
  nameKey: string;
  path: string;
  icon: typeof LayoutDashboard;
  badgeKey?: 'issues';
}

interface NavGroup {
  labelKey: string;
  items: NavLeaf[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    labelKey: 'nav.analyze',
    items: [
      { nameKey: 'nav.dashboard', path: '/dashboard', icon: LayoutDashboard },
      { nameKey: 'nav.issues', path: '/issues', icon: AlertCircle, badgeKey: 'issues' },
      { nameKey: 'nav.deployments', path: '/deployments', icon: Gauge },
    ],
  },
];

export default function Sidebar({
  issueCount = 0,
  onNavigate,
}: {
  issueCount?: number;
  onNavigate?: () => void;
}) {
  const t = useT();
  const { user, logout } = useAuth();
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridIntensity, setGridIntensity] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);

  useEffect(() => {
    let cancelled = false;
    gridService
      .getZoneIntensity(zone)
      .then((r) => {
        if (cancelled) return;
        setGridIntensity(r.data.marginal_carbon_intensity ?? r.data.carbon_intensity ?? null);
        setIsLive(r.data.is_live ?? false);
      })
      .catch(() => {
        if (cancelled) return;
        setGridIntensity(null);
        setIsLive(false);
      });
    return () => {
      cancelled = true;
    };
  }, [zone]);

  const displayName = user?.github_username || user?.username || 'Developer';
  const initials = displayName.slice(0, 2).toUpperCase();

  return (
    <aside className="flex flex-col w-56 h-full bg-[var(--gc-rail)] border-r border-[var(--gc-border-default)]">
      <div className="h-12 flex items-center gap-2 px-3 border-b border-[var(--gc-border-default)]">
        <BrandLogo size="sm" />
        <div className="flex flex-col leading-none min-w-0">
          <span className="font-semibold text-sm tracking-tight text-[var(--gc-text-primary)]">
            {t('app.name')}
          </span>
          <span className="text-[10px] font-mono text-[var(--gc-text-tertiary)] mt-0.5">
            {t('app.tagline')}
          </span>
        </div>
      </div>

      <div className="px-2 pt-2">
        <div className="flex items-center gap-2 px-2 py-1.5 rounded-md bg-[var(--gc-bg-subtle)] border border-[var(--gc-border-default)]">
          <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${isLive ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
          <span className="text-[10px] font-mono text-[var(--gc-text-tertiary)] truncate flex-1">{zone}</span>
          {gridIntensity !== null && (
            <span className="text-[11px] font-mono font-semibold text-[var(--gc-text-primary)] shrink-0">
              {gridIntensity}
            </span>
          )}
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-3 pt-1" aria-label={t('nav.primary')}>
        {NAV_GROUPS.map((group) => (
          <div key={group.labelKey}>
            <p className="sidebar-group-label">{t(group.labelKey)}</p>
            <div className="space-y-px">
              {group.items.map((item) => {
                const Icon = item.icon;
                const showBadge = item.badgeKey === 'issues' && issueCount > 0;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={onNavigate}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
                  >
                    <Icon size={15} className="shrink-0" />
                    <span className="flex-1 truncate">{t(item.nameKey)}</span>
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

      <div className="border-t border-[var(--gc-border-default)] p-2 space-y-1">
        <NavLink
          to="/settings"
          onClick={onNavigate}
          className={({ isActive }) => `sidebar-link ${isActive ? 'sidebar-link-active' : ''}`}
        >
          <Settings size={15} className="shrink-0" />
          <span className="flex-1">{t('nav.settings')}</span>
        </NavLink>

        <div className="flex items-center gap-2 px-1.5 py-1.5">
          {user?.avatar_url ? (
            <div className="w-8 h-8 rounded-full overflow-hidden border border-emerald-900/60 shrink-0 bg-[#161d19] shadow-2xs">
              <img src={user.avatar_url} alt={displayName} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-[#0e482f] text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-2xs">
              {initials}
            </div>
          )}
          <div className="min-w-0 flex-1">
            <p className="text-xs font-semibold text-[var(--gc-text-primary)] truncate">{displayName}</p>
            <p className="text-[10px] text-[var(--gc-text-tertiary)] truncate">
              {isLive ? t('grid.live') : t('grid.signedIn')}
            </p>
          </div>
          <button
            type="button"
            onClick={logout}
            className="shrink-0 text-[var(--gc-text-tertiary)] hover:text-rose-600 p-1 rounded"
            title={t('nav.signOut')}
            aria-label={t('nav.signOut')}
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
