import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, gridService } from '../services/greencodeApi';
import { ScanResult, Violation } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useAuth } from '../context/AuthContext';
import {
  GitBranch, Zap, Leaf, Activity, AlertTriangle, CheckCircle2,
  Play, Loader2, Copy, Sparkles, TrendingDown, DollarSign,
  Gauge, Search, Bot
} from 'lucide-react';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [scanData, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<{ carbon_intensity?: number } | null>(null);
  const [repoInput, setRepoInput] = useState('zeenat28-ui/greencode');
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatusMsg, setScanStatusMsg] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  const [selectedViolationIndex, setSelectedViolationIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING'>('ALL');
  const [copiedFix, setCopiedFix] = useState(false);

  useEffect(() => {
    gridService.getZoneIntensity(activeZone).then((r) => setGridData(r.data)).catch(() => setGridData(null));
  }, [activeZone]);

  const handleRunAudit = async () => {
    const repoToScan = repoInput.trim();
    if (!repoToScan) return;
    setIsScanning(true);
    setScanError(null);
    setScanStatusMsg(Cloning ...);
    try {
      const res = await scanService.scanGitHub(repoToScan);
      const violations = res.data.total_violations || 0;
      const lines = res.data.total_lines || 0;
      const cpuPct = violations > 0 ? 45 : 18;
      const watts = (15 + ((120 - 15) * cpuPct) / 100) * 1.2;
      const energyWh = (watts * Math.max(0.5, lines * 0.015)) / 3600;
      const carbonG = (energyWh / 1000) * (gridData?.carbon_intensity || 204.2);
      setScanData({ ...res.data, energy_wh: energyWh, carbon_g: carbonG });
      setScanStatusMsg(null);
    } catch (err: any) {
      setScanError(err?.response?.data?.detail || err?.message || 'Audit failed');
      setScanStatusMsg(null);
    } finally {
      setIsScanning(false);
    }
  };

  const handleCopyFix = (snippet: string) => {
    if (!snippet) return;
    navigator.clipboard.writeText(snippet);
    setCopiedFix(true);
    setTimeout(() => setCopiedFix(false), 2000);
  };

  const violationsList: Violation[] = useMemo(() => scanData?.violations || [], [scanData]);
  const filteredViolations = useMemo(() => {
    return violationsList.filter((v) => {
      const sev = (v.severity || 'MEDIUM').toUpperCase();
      const matchesSev = severityFilter === 'ALL' || 
        (severityFilter === 'CRITICAL' && sev === 'CRITICAL') ||
        (severityFilter === 'WARNING' && (sev === 'HIGH' || sev === 'MEDIUM'));
      const q = searchQuery.toLowerCase();
      const matchesQ = !q || v.title?.toLowerCase().includes(q) || v.file_path?.toLowerCase().includes(q);
      return matchesSev && matchesQ;
    });
  }, [violationsList, severityFilter, searchQuery]);

  const activeViolation = useMemo(() => {
    return filteredViolations[selectedViolationIndex] || filteredViolations[0] || null;
  }, [filteredViolations, selectedViolationIndex]);

  const projectedSavings = scanData ? ((scanData.total_violations || 0) * 0.73).toFixed(2) : '0.00';
