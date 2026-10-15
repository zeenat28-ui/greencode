import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Building, Check } from 'lucide-react';
import { Organization } from '../../types';
import { useTenant } from '../../context/TenantContext';
import { Button } from './Button';

interface TenantSwitcherProps {
  className?: string;
}

export default function TenantSwitcher({ className = '' }: TenantSwitcherProps) {
  const { currentOrg, availableOrgs, switchOrg, isLoading } = useTenant();
  const [open, setOpen] = useState(false);
  const [switching, setSwitching] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onClick);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onClick);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const handleSwitch = async (org: Organization) => {
    if (org.id === currentOrg?.id || switching) return;
    setSwitching(true);
    try {
      await switchOrg(org.id);
    } catch {
      console.error('[TenantSwitcher] Failed to switch tenant');
    } finally {
      setSwitching(false);
      setOpen(false);
    }
  };

  if (isLoading || availableOrgs.length <= 1) return null;

  const displayOrg = currentOrg || availableOrgs[0];

  return (
    <div
      className={`relative inline-block text-left ${className}`}
      ref={menuRef}
    >
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-mono"
      >
        {displayOrg?.name || 'Workspace'}
        <ChevronDown size={12} className="text-zinc-400" />
      </Button>

      {open && (
        <div className="absolute right-0 mt-1.5 w-56 card p-1 shadow-lg z-50">
          <div className="px-3 py-2 border-b border-[var(--gc-border-default)]">
            <p className="text-[10px] uppercase font-semibold text-[var(--gc-text-tertiary)] tracking-wider">
              Workspace
            </p>
          </div>
          <div className="py-1">
            {availableOrgs.map((org) => (
              <button
                key={org.id}
                onClick={() => handleSwitch(org)}
                disabled={switching || org.id === currentOrg?.id}
                className={`flex items-center gap-2.5 w-full px-3 py-2 text-left text-xs transition-colors ${
                  org.id === currentOrg?.id
                    ? 'bg-emerald-50 text-emerald-900 font-semibold'
                    : 'text-zinc-700 hover:bg-zinc-50'
                } disabled:opacity-50`}
              >
                <Building
                  size={13}
                  className={org.id === currentOrg?.id ? 'text-emerald-600' : 'text-zinc-400'}
                />
                <span className="flex-1 truncate">{org.name}</span>
                {displayOrg?.tier === 'enterprise' && (
                  <span className="text-[9px] font-mono bg-emerald-100 text-emerald-700 px-1.5 py-0.25 rounded">
                    {org.tier}
                  </span>
                )}
                {org.id === currentOrg?.id && (
                  <Check size={12} className="text-emerald-600 shrink-0" />
                )}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
