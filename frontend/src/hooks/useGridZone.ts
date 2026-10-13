import { useState, useEffect } from 'react';
import { gridService } from '../services/greencodeApi';
import { ZoneData } from '../types';
import { useLocalStorage } from './useLocalStorage';

interface GridZoneState {
  zone: string;
  intensity: number | null;
  isLive: boolean;
  loading: boolean;
  zoneData: ZoneData | null;
}

/**
 * Consolidates the grid-zone + carbon-intensity fetching pattern that was
 * previously duplicated across Navbar, Sidebar, Dashboard, Profiler, and Settings.
 *
 * Reads the user's preferred zone from localStorage (defaulting to US-CAL-CISO)
 * and fetches live marginal carbon intensity data.
 *
 * @param defaultZone - fallback zone if none stored in localStorage
 */
export function useGridZone(defaultZone: string = 'US-CAL-CISO') {
  const [storedZone, setStoredZone] = useLocalStorage('greencode_zone', defaultZone);
  const [state, setState] = useState<GridZoneState>({
    zone: storedZone,
    intensity: null,
    isLive: false,
    loading: true,
    zoneData: null,
  });

  const fetchZone = (zoneToFetch: string) => {
    if (!zoneToFetch) return;
    setState((prev) => ({ ...prev, loading: true }));
    gridService
      .getZoneIntensity(zoneToFetch)
      .then((r) => {
        const data = r.data;
        setState({
          zone: data.zone || zoneToFetch,
          intensity: data.marginal_carbon_intensity ?? data.carbon_intensity ?? null,
          isLive: data.is_live ?? false,
          loading: false,
          zoneData: data,
        });
      })
      .catch(() => {
        setState({
          zone: zoneToFetch,
          intensity: null,
          isLive: false,
          loading: false,
          zoneData: null,
        });
      });
  };

  useEffect(() => {
    fetchZone(storedZone);
  }, [storedZone]);

  return {
    zone: state.zone,
    zoneData: state.zoneData,
    intensity: state.intensity,
    isLive: state.isLive,
    loading: state.loading,
    setZone: setStoredZone,
    refetch: () => fetchZone(storedZone),
  };
}
