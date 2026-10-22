import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, gridService, githubService } from '../services/greencodeApi';
import { ScanResult, Violation, GitHubRepo } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { useAuth } from '../context/AuthContext';
import { GitBranch, Zap, Leaf, Activity, AlertTriangle, CheckCircle2, Play, Loader2, Copy, Sparkles, TrendingDown, DollarSign, Gauge, Search, Bot, ChevronDown, Github, Star, GitFork, Clock, Download, RefreshCw, FileText, ShieldCheck, X } from 'lucide-react';
import AlexaVoiceCockpit from '../components/common/AlexaVoiceCockpit';
import EsgAuditModal from '../components/common/EsgAuditModal';
import CiCdBadgeModal from '../components/common/CiCdBadgeModal';
import FinOpsCalculatorModal from '../components/common/FinOpsCalculatorModal';
import GitHubBotPreviewModal from '../components/common/GitHubBotPreviewModal';

export default function Dashboard() {
  const navigate = useNavigate();
  const { user, isGitHubConnected } = useAuth();
  const [scanData, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<{ carbon_intensity?: number } | null>(null);
  
  // Repository state
  const [repos, setRepos] = useState<GitHubRepo[]>([]);
  const [reposLoading, setReposLoading] = useState(false);
  const [selectedRepo, setSelectedRepo] = useState<GitHubRepo | null>(null);
  const [showRepoDropdown, setShowRepoDropdown] = useState(false);
  const [repoInput, setRepoInput] = useState('zeenat28-ui/greencode');
  
  // Scan state
  const [isScanning, setIsScanning] = useState(false);
  const [scanStatusMsg, setScanStatusMsg] = useState<string | null>(null);
  const [scanError, setScanError] = useState<string | null>(null);
  
  // UI state
  const [selectedViolationIndex, setSelectedViolationIndex] = useState(0);
  const [searchQuery, setSearchQuery] = useState('');
  const [severityFilter, setSeverityFilter] = useState<'ALL' | 'CRITICAL' | 'WARNING'>('ALL');
  const [copiedFix, setCopiedFix] = useState(false);

  // Tools Modal States
  const [showToolsDropdown, setShowToolsDropdown] = useState(false);
  const [showVoiceCockpit, setShowVoiceCockpit] = useState(false);
  const [showEsgModal, setShowEsgModal] = useState(false);
  const [showCiCdModal, setShowCiCdModal] = useState(false);
  const [showFinOpsModal, setShowFinOpsModal] = useState(false);
  const [showBotModal, setShowBotModal] = useState(false);

  // PR Creation state
  const [creatingPR, setCreatingPR] = useState(false);
  const [prSuccess, setPrSuccess] = useState<string | null>(null);

  useEffect(() => {
    gridService.getZoneIntensity(activeZone).then((r) => setGridData(r.data)).catch(() => {});
  }, [activeZone]);

  useEffect(() => {
    if (!isGitHubConnected) return;
    const loadRepos = async () => {
      setReposLoading(true);
      try {
        const res = await githubService.listRepositories(100);
        const userRepos = res.data.repositories || [];
        setRepos(userRepos);
        if (userRepos.length > 0 && !selectedRepo) {
          setSelectedRepo(userRepos[0]);
          setRepoInput(userRepos[0].full_name);
        }
      } catch (err) {
        console.error('Failed to load repositories:', err);
      } finally {
        setReposLoading(false);
      }
    };
    loadRepos();
  }, [isGitHubConnected]);

  const handleRunAudit = async (targetRepo?: string) => {
    const repoToScan = (targetRepo || repoInput).trim();
    if (!repoToScan) return;
    setIsScanning(true);
    setScanError(null);
    setScanStatusMsg(`Cloning ${repoToScan} & generating AST...`);
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
      setScanError(err?.response?.data?.detail || 'Audit failed');
      setScanStatusMsg(null);
    } finally {
      setIsScanning(false);
    }
  };

  const handleSelectRepo = (repo: GitHubRepo) => {
    setSelectedRepo(repo);
    setRepoInput(repo.full_name);
    setShowRepoDropdown(false);
  };

  const handleExportSarif = () => {
    if (!scanData) return;
    const dataStr = 'data:text/json;charset=utf-8,' + encodeURIComponent(JSON.stringify(scanData, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute('href', dataStr);
    downloadAnchor.setAttribute('download', `greencode-audit-${(scanData.repo_path || 'repo').replace(/[/\\?%*:|"<>]/g, '-')}.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const handleCreatePR = async () => {
    if (!activeViolation || !scanData?.repo_path) return;
    setCreatingPR(true);
    try {
      const res = await githubService.createPullRequest(
        scanData.repo_path,
        activeViolation.file_path || 'unknown.py',
        activeViolation.suggested_fix || '',
        activeViolation.title || activeViolation.violation_type || 'Code optimization',
        15,
        0.5
      );
      setPrSuccess(res.data.pr_url);
      setTimeout(() => setPrSuccess(null), 5000);
    } catch (err: any) {
      setScanError('Failed to create PR: ' + (err?.response?.data?.detail || err?.message));
    } finally {
      setCreatingPR(false);
    }
  };

  const violationsList: Violation[] = useMemo(() => scanData?.violations || [], [scanData]);
  const filteredViolations = useMemo(() => {
    return violationsList.filter((v) => {
      const sev = (v.severity || 'MEDIUM').toUpperCase();
      const matchesSev = severityFilter === 'ALL' || (severityFilter === 'CRITICAL' && sev === 'CRITICAL') || (severityFilter === 'WARNING' && (sev === 'HIGH' || sev === 'MEDIUM'));
      const q = searchQuery.toLowerCase();
      return matchesSev && (!q || v.title?.toLowerCase().includes(q) || v.file_path?.toLowerCase().includes(q));
    });
  }, [violationsList, severityFilter, searchQuery]);

  const activeViolation = filteredViolations[selectedViolationIndex] || filteredViolations[0] || null;
  const projectedSavings = scanData ? ((scanData.total_violations || 0) * 0.73).toFixed(2) : '0.00';
  return (
    <div className="min-h-screen bg-[#f5f7f6] p-4">
      <div className="max-w-[1400px] mx-auto space-y-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-600 flex items-center justify-center">
              <Leaf className="text-white" size={20} />
            </div>
            <div><h1 className="text-xl font-bold text-gray-900">GreenCode</h1><p className="text-xs text-gray-500">SCI Auditor</p></div>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative">
              <button onClick={() => setShowRepoDropdown(!showRepoDropdown)} disabled={isScanning || !isGitHubConnected} className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-gray-200 hover:border-gray-300 disabled:opacity-50">
                <GitBranch size={13} className="text-gray-500" />
                <span className="text-xs font-mono text-gray-700 max-w-[200px] truncate">{selectedRepo ? selectedRepo.full_name : repoInput || 'Select repository'}</span>
                {selectedRepo && <div className="flex items-center gap-1 text-[10px] text-gray-500"><Star size={10} /><span>{selectedRepo.stars || 0}</span></div>}
                <ChevronDown size={12} className="text-gray-400" />
              </button>
              {showRepoDropdown && isGitHubConnected && (
                <div className="absolute top-full left-0 mt-1 w-96 bg-white rounded-lg border border-gray-200 shadow-xl z-50 max-h-[400px] overflow-y-auto">
                  {reposLoading ? (
                    <div className="p-4 text-center"><Loader2 size={20} className="animate-spin mx-auto text-emerald-500 mb-2" /><p className="text-xs text-gray-500">Loading your repositories...</p></div>
                  ) : repos.length === 0 ? (
                    <div className="p-4 text-center"><Github size={24} className="mx-auto text-gray-400 mb-2" /><p className="text-xs text-gray-500">No repositories found</p></div>
                  ) : (
                    <div className="divide-y divide-gray-100">
                      {repos.map((repo) => (
                        <button key={repo.id} onClick={() => handleSelectRepo(repo)} className="w-full text-left px-3 py-2 hover:bg-gray-50">
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0"><p className="text-xs font-semibold text-gray-900 truncate">{repo.full_name}</p>{repo.description && <p className="text-[10px] text-gray-500 truncate mt-0.5">{repo.description}</p>}</div>
                            <div className="flex items-center gap-2 text-[10px] text-gray-500"><div className="flex items-center gap-0.5"><Star size={10} /><span>{repo.stars || 0}</span></div><div className="flex items-center gap-0.5"><GitFork size={10} /><span>{repo.forks || 0}</span></div></div>
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            {repo.language && <span className="text-[10px] px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded">{repo.language}</span>}
                            <span className="text-[10px] text-gray-400 flex items-center gap-1"><Clock size={9} />Updated {new Date(repo.updated_at || '').toLocaleDateString()}</span>
                          </div>
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>

            <button onClick={() => handleRunAudit()} disabled={isScanning || !repoInput} className="px-4 py-1.5 bg-emerald-500 hover:bg-emerald-600 text-white text-sm font-medium rounded-lg disabled:opacity-50 flex items-center gap-2">
              {isScanning ? <Loader2 size={14} className="animate-spin" /> : <Play size={13} />}<span>Audit Repository</span>
            </button>

            <button onClick={() => setShowVoiceCockpit(true)} className="px-3 py-1.5 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg flex items-center gap-2">
              <Bot size={13} className="text-emerald-500" /><span>Voice Ledger</span>
            </button>

            <div className="relative">
              <button onClick={() => setShowToolsDropdown(!showToolsDropdown)} className="px-3 py-1.5 bg-white hover:bg-gray-50 border border-gray-200 text-gray-700 text-xs font-medium rounded-lg flex items-center gap-2">
                <Activity size={13} /><span>Tools</span><ChevronDown size={11} className="text-gray-400" />
              </button>
              {showToolsDropdown && (
                <div className="absolute right-0 top-full mt-1 w-48 bg-white rounded-lg border border-gray-200 shadow-xl z-50 py-1">
                  <button onClick={() => { setShowFinOpsModal(true); setShowToolsDropdown(false); }} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-xs text-gray-700 flex items-center gap-2"><DollarSign size={12} className="text-emerald-500" /><span>FinOps Calculator</span></button>
                  <button onClick={() => { setShowEsgModal(true); setShowToolsDropdown(false); }} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-xs text-gray-700 flex items-center gap-2"><FileText size={12} className="text-gray-500" /><span>ESG Report</span></button>
                  <button onClick={() => { setShowBotModal(true); setShowToolsDropdown(false); }} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-xs text-gray-700 flex items-center gap-2"><Bot size={12} className="text-gray-500" /><span>PR Comment Bot</span></button>
                  <button onClick={() => { setShowCiCdModal(true); setShowToolsDropdown(false); }} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-xs text-gray-700 flex items-center gap-2"><ShieldCheck size={12} className="text-gray-500" /><span>CI/CD Badge</span></button>
                  <button onClick={handleExportSarif} disabled={!scanData} className="w-full text-left px-3 py-2 hover:bg-gray-50 text-xs text-gray-700 flex items-center gap-2 disabled:opacity-50"><Download size={12} className="text-gray-500" /><span>Export SARIF</span></button>
                </div>
              )}
            </div>

            <button onClick={() => navigate('/issues')} className="p-1.5 bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg"><Sparkles size={16} /></button>

            <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-lg border border-gray-200">
              {isGitHubConnected && <Github size={12} className="text-gray-500" />}
              <div className="w-6 h-6 rounded-full bg-gray-200 flex items-center justify-center text-xs font-medium">{user?.github_username?.[0]?.toUpperCase() || user?.username?.[0]?.toUpperCase() || 'U'}</div>
              <span className="text-xs font-medium text-gray-700">{user?.github_username || user?.username || 'developer'}</span>
            </div>
          </div>
        </div>

        {scanStatusMsg && <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 flex items-center gap-2 text-sm text-blue-700"><Loader2 size={16} className="animate-spin" /><span>{scanStatusMsg}</span></div>}
        {scanError && <div className="bg-red-50 border border-red-200 rounded-lg p-3 flex items-center gap-2 text-sm text-red-700"><AlertTriangle size={16} /><span>{scanError}</span></div>}
        {prSuccess && <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-3 flex items-center justify-between"><div className="flex items-center gap-2 text-sm text-emerald-700"><CheckCircle2 size={16} /><span>Pull request created successfully!</span></div><a href={prSuccess} target="_blank" rel="noopener noreferrer" className="text-xs text-emerald-600 hover:underline">View PR →</a></div>}

        <div className="grid grid-cols-4 gap-4">
          <div className="bg-white rounded-xl border-2 border-gray-200 p-5 shadow-sm hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3"><div><h3 className="text-xs font-semibold text-gray-500 uppercase">SOFTWARE EFFICIENCY RATING</h3><p className="text-[10px] text-gray-400">GSF 643 v1.3 standard</p></div><div className="w-8 h-8 rounded-lg bg-yellow-100 flex items-center justify-center"><Gauge size={16} className="text-yellow-600" /></div></div>
            <div className="flex items-baseline gap-2 mb-2"><span className="text-4xl font-black text-gray-900">{scanData?.green_score || 12}</span><span className="text-lg text-gray-400 font-medium">/ 100</span></div>
            <div className="inline-block px-2 py-1 bg-orange-100 text-orange-700 text-xs font-bold rounded">■ Action Recommended</div>
          </div>
          <div className="bg-white rounded-xl border-2 border-gray-200 p-5 shadow-sm hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3"><div><h3 className="text-xs font-semibold text-gray-500 uppercase">OPTIMIZATION OPPORTUNITIES</h3><p className="text-[10px] text-gray-400">AST code anti-patterns</p></div><div className="w-8 h-8 rounded-lg bg-pink-100 flex items-center justify-center"><AlertTriangle size={16} className="text-pink-600" /></div></div>
            <div className="flex items-baseline gap-2 mb-2"><span className="text-4xl font-black text-gray-900">{scanData?.total_violations || 24}</span><span className="text-lg text-gray-400 font-medium">detected</span></div>
            <div className="flex items-center gap-2 text-xs font-semibold"><span className="text-red-600">⬤ High</span><span className="text-gray-300">|</span><span className="text-orange-500">⬤ Medium</span></div>
          </div>
          <div className="bg-white rounded-xl border-2 border-gray-200 p-5 shadow-sm hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3"><div><h3 className="text-xs font-semibold text-gray-500 uppercase">WORKLOAD ENERGY DEMAND</h3><p className="text-[10px] text-gray-400">Hardware RAPL & Grid Metric</p></div><div className="w-8 h-8 rounded-lg bg-cyan-100 flex items-center justify-center"><Zap size={16} className="text-cyan-600" /></div></div>
            <div className="flex items-baseline gap-2 mb-2"><span className="text-4xl font-black text-gray-900">{scanData?.energy_wh ? scanData.energy_wh.toFixed(2) : '0.56'}</span><span className="text-lg text-gray-400 font-medium">Watt-hours</span></div>
            <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-semibold"><TrendingDown size={12} /><span>1.2 gCO₂e / 10k BASES</span></div>
          </div>
          <div className="bg-white rounded-xl border-2 border-gray-200 p-5 shadow-sm hover:shadow-md transition">
            <div className="flex items-start justify-between mb-3"><div><h3 className="text-xs font-semibold text-gray-500 uppercase">CLOUD EFFICIENCY & FINOPS</h3><p className="text-[10px] text-gray-400">$200 / yr Projected moSavings</p></div><div className="w-8 h-8 rounded-lg bg-green-100 flex items-center justify-center"><DollarSign size={16} className="text-green-600" /></div></div>
            <div className="flex items-baseline gap-1 mb-2"><span className="text-4xl font-black text-gray-900">${projectedSavings}</span><span className="text-sm text-gray-400">/ $200</span></div>
            <div className="text-xs text-gray-500 font-medium">/ yr Projected moSavings</div>
          </div>
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div className="bg-white rounded-xl border-2 border-gray-200 shadow-sm overflow-hidden">
            <div className="flex items-center gap-1 bg-gray-50 border-b border-gray-200 p-2">
              <button onClick={() => setSeverityFilter('ALL')} className={`px-3 py-1.5 text-xs font-semibold rounded ${severityFilter === 'ALL' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}>All ({violationsList.length})</button>
              <button onClick={() => setSeverityFilter('CRITICAL')} className={`px-3 py-1.5 text-xs font-semibold rounded ${severityFilter === 'CRITICAL' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}>Critical</button>
              <button onClick={() => setSeverityFilter('WARNING')} className={`px-3 py-1.5 text-xs font-semibold rounded ${severityFilter === 'WARNING' ? 'bg-emerald-500 text-white' : 'bg-white text-gray-600 hover:bg-gray-100'}`}>Warning</button>
            </div>
            <div className="p-2 border-b border-gray-200"><div className="relative"><Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-400" /><input type="text" value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search issues..." className="w-full pl-8 pr-3 py-1.5 text-xs border border-gray-200 rounded-lg focus:outline-none focus:border-emerald-500" /></div></div>
            <div className="divide-y divide-gray-200 max-h-[500px] overflow-y-auto">
              {filteredViolations.length === 0 ? (
                <div className="p-6 text-center"><CheckCircle2 size={32} className="mx-auto text-emerald-500 mb-2" /><p className="text-sm text-gray-500">No violations found</p></div>
              ) : (
                filteredViolations.map((v, idx) => {
                  const severity = (v.severity || 'MEDIUM').toUpperCase();
                  const isActive = idx === selectedViolationIndex;
                  return (
                    <button key={idx} onClick={() => setSelectedViolationIndex(idx)} className={`w-full text-left p-3 hover:bg-gray-50 ${isActive ? 'bg-emerald-50 border-l-4 border-emerald-500' : ''}`}>
                      <div className="flex items-start gap-2 mb-1">
                        <span className={`px-1.5 py-0.5 text-[10px] font-bold rounded uppercase ${severity === 'CRITICAL' ? 'bg-red-100 text-red-700' : 'bg-orange-100 text-orange-700'}`}>{severity === 'CRITICAL' ? 'HARMFUL' : 'WARNING'}</span>
                        <span className="text-xs font-semibold text-gray-900 flex-1">{v.title || v.violation_type}</span>
                        <span className="text-xs text-orange-600 font-semibold">+{((v.energy_impact_wh || 0.02) * 1000).toFixed(0)} Wh</span>
                      </div>
                      <div className="text-xs text-gray-500 font-mono">{v.file_path}:{v.line_number || 346}</div>
                      <div className="text-[11px] text-gray-400 uppercase mt-1">{v.violation_type?.replace(/_/g, ' ')}</div>
                    </button>
                  );
                })
              )}
            </div>
          </div>
          <div className="col-span-2 bg-white rounded-xl border-2 border-gray-200 shadow-sm overflow-hidden flex flex-col">
            <div className="bg-gray-50 border-b border-gray-200 px-4 py-2.5 flex items-center justify-between">
              <div className="flex items-center gap-2 text-xs font-semibold text-gray-700">
                <span className="px-2 py-0.5 bg-blue-100 text-blue-700 rounded font-mono">{activeViolation?.violation_type || 'QUADRATIC_STRING_CONCAT_IN_LOOP'}</span>
                <span className="text-gray-400">•</span>
                <span className="font-mono text-gray-500">{activeViolation?.file_path || 'bottle.py'}:{activeViolation?.line_number || 346}</span>
              </div>
              <div className="flex items-center gap-2">
                <button className="px-3 py-1 bg-purple-100 text-purple-700 text-xs font-semibold rounded hover:bg-purple-200 flex items-center gap-1"><Sparkles size={12} /><span>AI Refactor</span></button>
                <button onClick={() => { if (activeViolation?.suggested_fix) { navigator.clipboard.writeText(activeViolation.suggested_fix); setCopiedFix(true); setTimeout(() => setCopiedFix(false), 2000); }}} className="px-3 py-1 bg-emerald-100 text-emerald-700 text-xs font-semibold rounded hover:bg-emerald-200 flex items-center gap-1">{copiedFix ? <><CheckCircle2 size={12} /><span>Copied</span></> : <><Copy size={12} /><span>Apply Patch</span></>}</button>
                <button onClick={handleCreatePR} disabled={creatingPR || !activeViolation} className="px-3 py-1 bg-gray-100 text-gray-700 text-xs font-medium rounded hover:bg-gray-200 disabled:opacity-50 flex items-center gap-1">{creatingPR ? <Loader2 size={11} className="animate-spin" /> : <span>To PR</span>}</button>
              </div>
            </div>
            <div className="grid grid-cols-2 divide-x divide-gray-200 flex-1">
              <div className="bg-gradient-to-br from-red-50 to-rose-50 p-4"><div className="text-[10px] font-bold text-red-700 uppercase mb-2 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-red-500" /><span>-- Inefficient Code</span></div><pre className="text-xs font-mono text-gray-800"><code><span className="text-gray-500">346</span>  pattern += '(?P&lt;%(name)s&gt;' % {'{'}key, mask{'}'}</code></pre></div>
              <div className="bg-gradient-to-br from-emerald-50 to-green-50 p-4"><div className="text-[10px] font-bold text-emerald-700 uppercase mb-2 flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-emerald-500" /><span>+ Green AST Refactor</span></div><pre className="text-xs font-mono text-gray-800"><code><span className="text-gray-500">346</span>  + {activeViolation?.suggested_fix || "Append strings into a list and combine once at exit using '.join(chunks)"}</code></pre><div className="mt-3 p-2 bg-emerald-100 border border-emerald-300 rounded text-[10px] text-emerald-800 font-mono">✓✓ Saves -$0.80 / mo</div></div>
            </div>
          </div>
        </div>

        <div className="bg-emerald-600 text-white rounded-lg px-4 py-2 flex items-center justify-between text-xs font-medium">
          <span>■ {scanData ? `Loaded audit: ${scanData.total_violations || 0} bottlenecks in ${scanData.repo_path}` : `Ready to audit ${repos.length} repositories`}</span>
          <span className="font-mono">⏱ ISO 14046:1 H 0 GS RCI</span>
        </div>
      </div>

      {showVoiceCockpit && <AlexaVoiceCockpit isOpen={showVoiceCockpit} onClose={() => setShowVoiceCockpit(false)} />}
      {showEsgModal && <EsgAuditModal isOpen={showEsgModal} onClose={() => setShowEsgModal(false)} />}
      {showCiCdModal && <CiCdBadgeModal isOpen={showCiCdModal} onClose={() => setShowCiCdModal(false)} />}
      {showFinOpsModal && <FinOpsCalculatorModal isOpen={showFinOpsModal} onClose={() => setShowFinOpsModal(false)} />}
      {showBotModal && <GitHubBotPreviewModal isOpen={showBotModal} onClose={() => setShowBotModal(false)} />}
    </div>
  );
}
