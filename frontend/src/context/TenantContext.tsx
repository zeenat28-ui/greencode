import { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { Organization } from '../types';
import { tenantService } from '../services/greencodeApi';
import { setAccessToken, setRefreshToken, getRefreshToken, clearSession } from '../services/api';
import { useAuth } from './AuthContext';

interface TenantContextType {
  currentOrg: Organization | null;
  availableOrgs: Organization[];
  isLoading: boolean;
  switchOrg: (orgId: number) => Promise<void>;
  refreshOrgs: () => Promise<void>;
}

const TenantContext = createContext<TenantContextType | undefined>(undefined);

export const useTenant = () => {
  const ctx = useContext(TenantContext);
  if (!ctx) throw new Error('useTenant must be used within TenantProvider');
  return ctx;
};

export const TenantProvider = ({ children }: { children: ReactNode }) => {
  const { isAuthenticated, refreshUser } = useAuth();
  const [availableOrgs, setAvailableOrgs] = useState<Organization[]>([]);
  const [currentOrg, setCurrentOrg] = useState<Organization | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchOrgs = useCallback(async () => {
    if (!isAuthenticated) {
      setAvailableOrgs([]);
      setCurrentOrg(null);
      setIsLoading(false);
      return;
    }
    try {
      const res = await tenantService.getOrganizations();
      const orgs: Organization[] = res.data.organizations || [];
      setAvailableOrgs(orgs);

      const currentOrgId = res.data.current_org_id;
      const found = orgs.find((o) => o.id === currentOrgId) || orgs[0] || null;
      setCurrentOrg(found);
    } catch (e) {
      console.error('[TenantProvider] Failed to fetch organizations:', e);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthenticated]);

  const switchOrg = useCallback(async (orgId: number) => {
    try {
      const res = await tenantService.switchOrganization(orgId);

      if (res.data.access_token) {
        setAccessToken(res.data.access_token);
      }
      if (res.data.refresh_token) {
        setRefreshToken(res.data.refresh_token);
      }

      const org: Organization = res.data.organization;
      setCurrentOrg(org);

      window.dispatchEvent(new CustomEvent('tenant:switched', { detail: { org_id: orgId } }));

      if (refreshUser) {
        await refreshUser();
      }
    } catch (e) {
      clearSession();
      window.dispatchEvent(new CustomEvent('auth:logout'));
      throw e;
    }
  }, [refreshUser]);

  const refreshOrgs = useCallback(async () => {
    setIsLoading(true);
    await fetchOrgs();
  }, [fetchOrgs]);

  useEffect(() => {
    let cancelled = false;

    const init = async () => {
      if (!isAuthenticated) {
        setAvailableOrgs([]);
        setCurrentOrg(null);
        setIsLoading(false);
        return;
      }
      if (!getRefreshToken()) {
        setIsLoading(false);
        return;
      }
      try {
        await fetchOrgs();
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    init();
    return () => { cancelled = true; };
  }, [fetchOrgs, isAuthenticated]);

  return (
    <TenantContext.Provider
      value={{
        currentOrg,
        availableOrgs,
        isLoading,
        switchOrg,
        refreshOrgs,
      }}
    >
      {children}
    </TenantContext.Provider>
  );
};
