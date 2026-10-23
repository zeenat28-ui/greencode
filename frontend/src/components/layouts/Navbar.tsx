import { Link, NavLink, useLocation } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { ShieldCheck, Loader2, LogOut, ChevronDown, Settings } from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAuth } from '../../context/AuthContext';
import TenantSwitcher from '../primitives/TenantSwitcher';
import { useT } from '../../i18n/I18nContext';
import BrandLogo from '../common/BrandLogo';

export default function Navbar() {
  const t = useT();
  const { user, logout } = useAuth();
  const location = useLocation();
  const [zone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [threshold] = useLocalStorage('greencode_threshold', 75);
  const [gridIntensity, setGridIntensity] = useState<number | null>(null);
  const [isLive, setIsLive] = useState(false);
  const [gridLoading, setGridLoading] = useState(true);
  const [menuOpen, setMenuOpen] = useState(false);
  const [sectionsMenuOpen, setSectionsMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const sectionsRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setGridLoading(true);
    gridService
      .getZoneIntensity(zone)
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
    if (!menuOpen && !sectionsMenuOpen) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
      if (sectionsRef.current && !sectionsRef.current.contains(e.target as Node)) setSectionsMenuOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setMenuOpen(false);
        setSectionsMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [menuOpen, sectionsMenuOpen]);

  const displayName = user?.github_username || user?.username || 'Developer';
  const avatar = user?.avatar_url;
  const explorePaths = [
    '/history',
    '/profiler',
    '/cloud-carbon',
    '/budgets',
    '/policies',
    '/deployments',
    '/reports',
  ];
  const exploreActive = explorePaths.includes(location.pathname);

  return (
    <header className="gc-console-topbar h-14 shrink-0 flex items-center gap-3 px-3 sm:px-5">
      <Link to="/dashboard" className="gc-console-brand flex items-center gap-2 shrink-0" aria-label={t('app.name')}>
        <BrandLogo size="sm" />
        <span className="font-bold text-sm tracking-tight">GreenCode</span>
      </Link>

      <nav className="gc-topnav flex items-center gap-1 ml-2 sm:ml-6" aria-label={t('nav.primary')}>
        {[
          { to: '/dashboard', label: t('nav.dashboard') },
          { to: '/scan', label: t('nav.scan') },
          { to: '/issues', label: t('nav.issues') },
        ].map(({ to, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `gc-topnav-link ${isActive ? 'gc-topnav-link-active' : ''}`}
          >
            {label}
          </NavLink>
        ))}
        <div className="relative" ref={sectionsRef}>
          <button
            type="button"
            className={`gc-topnav-link ${sectionsMenuOpen || exploreActive ? 'gc-topnav-link-active' : ''}`}
            aria-haspopup="menu"
            aria-expanded={sectionsMenuOpen}
            onClick={() => setSectionsMenuOpen((open) => !open)}
          >
            {t('nav.explore')} <ChevronDown size={12} className="ml-1" />
          </button>
          {sectionsMenuOpen && (
            <div role="menu" className="gc-more-dropdown card absolute left-0 top-full z-50 mt-2 p-2 shadow-lg">
              {[
                {
                  title: 'nav.workspace',
                  links: [['/history', 'nav.history']],
                },
                {
                  title: 'nav.insights',
                  links: [
                    ['/profiler', 'nav.profiler'],
                    ['/cloud-carbon', 'nav.cloudCarbon'],
                  ],
                },
                {
                  title: 'nav.governance',
                  links: [
                    ['/budgets', 'nav.budgets'],
                    ['/policies', 'nav.policies'],
                    ['/deployments', 'nav.deployments'],
                    ['/reports', 'nav.reports'],
                  ],
                },
              ].map((section) => (
                <div key={section.title} className="gc-nav-section">
                  <p className="gc-nav-section-label">{t(section.title)}</p>
                  {section.links.map(([to, labelKey]) => (
                    <NavLink
                      key={to}
                      to={to}
                      role="menuitem"
                      onClick={() => setSectionsMenuOpen(false)}
                      className={({ isActive }) => `gc-more-link ${isActive ? 'gc-more-link-active' : ''}`}
                    >
                      {t(labelKey)}
                    </NavLink>
                  ))}
                </div>
              ))}
            </div>
          )}
        </div>
      </nav>

      <div className="flex-1 min-w-0" />

      <div className="hidden xl:flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--gc-bg-subtle)] border border-[var(--gc-border-default)] text-[11px] font-mono text-[var(--gc-text-secondary)]">
        {gridLoading ? (
          <Loader2 size={11} className="animate-spin" />
        ) : (
          <span className={`w-1.5 h-1.5 rounded-full ${isLive ? 'bg-emerald-500' : 'bg-zinc-400'}`} />
        )}
        <span>{zone}</span>
        {gridIntensity !== null && !gridLoading && (
          <span className="font-semibold text-[var(--gc-text-primary)]">
            {gridIntensity} {t('topbar.gridUnit')}
          </span>
        )}
      </div>

      <div className="hidden lg:flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 text-[11px] font-mono font-medium text-emerald-800 dark:text-emerald-300">
        <ShieldCheck size={12} />
        {t('topbar.gate', { threshold })}
      </div>

      <TenantSwitcher />

      <div className="relative" ref={menuRef}>
        <button
          type="button"
          onClick={() => setMenuOpen((o) => !o)}
          aria-haspopup="menu"
          aria-expanded={menuOpen}
          className="flex items-center gap-1.5 pl-0.5 pr-1.5 py-0.5 rounded-full hover:bg-[var(--gc-bg-subtle)] border border-transparent hover:border-[var(--gc-border-default)]"
        >
          {avatar ? (
            <div className="w-8 h-8 rounded-full overflow-hidden border border-emerald-900/60 shrink-0 bg-[#161d19] shadow-2xs">
              <img src={avatar} alt={displayName} className="w-full h-full object-cover" />
            </div>
          ) : (
            <div className="w-8 h-8 rounded-full bg-[#0e482f] text-white flex items-center justify-center text-xs font-bold shrink-0 shadow-2xs">
              {displayName.slice(0, 2).toUpperCase()}
            </div>
          )}
          <span className="hidden md:inline text-xs font-medium text-[var(--gc-text-secondary)] max-w-[7.5rem] truncate">
            {displayName}
          </span>
          <ChevronDown size={12} className={`text-[var(--gc-text-tertiary)] ${menuOpen ? 'rotate-180' : ''}`} />
        </button>

        {menuOpen && (
          <div role="menu" className="absolute right-0 mt-2 w-56 card p-1.5 shadow-lg z-50">
            <div className="px-2.5 py-2 border-b border-[var(--gc-border-default)]">
              <p className="text-xs font-semibold text-[var(--gc-text-primary)] truncate">{displayName}</p>
              <p className="text-[11px] text-[var(--gc-text-tertiary)] truncate">{user?.email}</p>
              {user?.github_token_masked && (
                <p className="text-[11px] font-mono text-[var(--gc-text-tertiary)] mt-1">
                  {t('topbar.token', { masked: user.github_token_masked })}
                </p>
              )}
            </div>
            <Link
              to="/settings"
              onClick={() => setMenuOpen(false)}
              className="flex items-center gap-2 w-full px-2.5 py-1.5 rounded-md text-xs font-medium text-[var(--gc-text-secondary)] hover:bg-[var(--gc-bg-subtle)] mt-1"
              role="menuitem"
            >
              <Settings size={13} />
              {t('nav.settings')}
            </Link>
            <button
              type="button"
              onClick={() => {
                setMenuOpen(false);
                logout();
              }}
              className="flex items-center gap-2 w-full px-2.5 py-1.5 rounded-md text-xs font-medium text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-950"
              role="menuitem"
            >
              <LogOut size={13} />
              {t('nav.signOut')}
            </button>
          </div>
        )}
      </div>
    </header>
  );
}
