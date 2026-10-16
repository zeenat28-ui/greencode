import { Link } from 'react-router-dom';
import { useEffect, useRef, useState } from 'react';
import { Menu, X, ShieldCheck, Loader2, LogOut, Github, ChevronDown, Settings } from 'lucide-react';
import { gridService } from '../../services/greencodeApi';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { useAuth } from '../../context/AuthContext';
import TenantSwitcher from '../primitives/TenantSwitcher';
import { useT } from '../../i18n/I18nContext';

interface NavbarProps {
  navOpen?: boolean;
  onToggleNav?: () => void;
}

export default function Navbar({ navOpen, onToggleNav }: NavbarProps) {
  const t = useT();
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
    <header className="h-12 shrink-0 bg-[var(--gc-rail)] border-b border-[var(--gc-border-default)] flex items-center gap-2 px-3">
      <button
        type="button"
        className="lg:hidden inline-flex items-center justify-center w-8 h-8 rounded-md border border-[var(--gc-border-default)] text-[var(--gc-text-secondary)]"
        onClick={onToggleNav}
        aria-label={navOpen ? t('nav.closeMenu') : t('nav.openMenu')}
      >
        {navOpen ? <X size={16} /> : <Menu size={16} />}
      </button>

      <div className="flex-1 min-w-0" />

      <div className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded-md bg-[var(--gc-bg-subtle)] border border-[var(--gc-border-default)] text-[11px] font-mono text-[var(--gc-text-secondary)]">
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

      <div className="hidden sm:flex items-center gap-1 px-2 py-1 rounded-md border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950 text-[11px] font-mono font-medium text-emerald-800 dark:text-emerald-300">
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
