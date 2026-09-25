import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { scanService, gridService, githubService } from '../services/greencodeApi';
import { ScanResult, ZoneData } from '../types';
import { useLocalStorage } from '../hooks/useLocalStorage';
import { GitBranch, Upload, FolderOpen, Loader2, Search, AlertCircle, FileCode, CheckCircle2, X } from 'lucide-react';

interface UploadState {
  file: File | null;
  progress: number;
  status: 'idle' | 'uploading' | 'scanning' | 'complete' | 'error';
}

export default function ScanRepository() {
  const navigate = useNavigate();
  const [, setScanData] = useLocalStorage<ScanResult | null>('greencode_scan_data', null);
  const [ghToken] = useLocalStorage<string>('greencode_gh_token', '');
  const [activeZone] = useLocalStorage('greencode_zone', 'US-CAL-CISO');
  const [gridData, setGridData] = useState<ZoneData | null>(null);
  const [selectedTab, setSelectedTab] = useState<'local' | 'github' | 'upload'>('local');
  const [scanTarget, setScanTarget] = useState('samples');
  const [isScanning, setIsScanning] = useState(false);
  const [scanError, setScanError] = useState<string | null>(null);
  const [uploadedFile, setUploadedFile] = useState<UploadState>({ file: null, progress: 0, status: 'idle' });
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [ghRepos, setGhRepos] = useState<any[]>([]);
  const [ghLoading, setGhLoading] = useState(false);

  useEffect(() => {
    loadGridData();
  }, [activeZone]);

  const loadGridData = async () => {
    try {
      const resp = await gridService.getZoneIntensity(activeZone);
      setGridData(resp.data);
    } catch {
      setGridData(null);
    }
  };

  const loadGhRepos = async () => {
    setGhLoading(true);
    try {
      const resp = await githubService.listRepositories(ghToken || undefined);
      setGhRepos(resp.data.repositories || []);
    } catch {
      setGhRepos([]);
    } finally {
      setGhLoading(false);
    }
  };

  useEffect(() => {
    loadGhRepos();
  }, [ghToken]);

  function estimateEnergy(result: any): number {
    const lines = result.total_lines || 0;
    const violations = result.total_violations || 0;
    const cpuPct = violations > 0 ? 45 : 18;
    const memMb = Math.max(64, lines * 0.8);
    const duration = Math.max(0.5, lines * 0.015);
    const pIdle = 15, pPeak = 120, pMem = 0.3725, pue = 1.2;
    const cpuW = pIdle + ((pPeak - pIdle) * cpuPct / 100);
    const memW = (memMb / 1024) * pMem;
    const totalW = (cpuW + memW) * pue;
    return (totalW * duration) / 3600;
  }

  function estimateCarbon(result: any): number {
    const energyWh = result.energy_wh || estimateEnergy(result);
    const intensity = gridData?.carbon_intensity || 215;
    return (energyWh / 1000) * intensity;
  }

  const handleLocalScan = async () => {
    const target = scanTarget.trim();
    if (!target) {
      setScanError('Please enter a valid directory path or use "samples".');
      return;
    }
    setIsScanning(true);
    setScanError(null);
    try {
      const resp = await scanService.scanRepository(target);
      const result = resp.data;
      result.energy_wh = result.energy_wh || estimateEnergy(result);
      result.carbon_g = result.carbon_g || estimateCarbon(result);
      setScanData(result);
      navigate('/dashboard');
    } catch (err: any) {
      setScanError(err.response?.data?.detail || 'Scan failed. Please verify the folder path exists on the host machine.');
    } finally {
      setIsScanning(false);
    }
  };

  // Bug fix #7: handleZipUpload sets status 'idle' when selected, never 'uploading'
  const handleZipUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setScanError('Please select a valid .zip archive file.');
      return;
    }
    setScanError(null);
    setUploadedFile({ file, progress: 0, status: 'idle' });
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.zip')) {
      setScanError('Please drop a valid .zip archive file.');
      return;
    }
    setScanError(null);
    setUploadedFile({ file, progress: 0, status: 'idle' });
  };

  const handleUploadScan = async () => {
    if (!uploadedFile.file) {
      setScanError('Please select or drop a ZIP archive first.');
      return;
    }
    setUploadedFile(prev => ({ ...prev, status: 'uploading' }));
    setScanError(null);
    try {
      const resp = await scanService.uploadZip(uploadedFile.file);
      const result = resp.data;
      result.energy_wh = result.energy_wh || estimateEnergy(result);
      result.carbon_g = result.carbon_g || estimateCarbon(result);
      result.is_github = false;
      setScanData(result);
      setUploadedFile({ file: null, progress: 0, status: 'complete' });
      navigate('/dashboard');
    } catch (err: any) {
      setUploadedFile(prev => ({ ...prev, status: 'error' }));
      setScanError(err.response?.data?.detail || 'Archive audit failed. Ensure the ZIP contains valid source code.');
    }
  };

  // Bug fix #8: Real GitHub scan calling backend GitHub download & audit endpoint
  const handleGitHubScan = async () => {
    const rawTarget = scanTarget.trim();
    if (!rawTarget) {
      setScanError('Please enter a GitHub repository (e.g. owner/repo or https://github.com/owner/repo).');
      return;
    }

    const cleanSlug = rawTarget
      .replace(/^https?:\/\/github\.com\//i, '')
      .replace(/\.git$/i, '')
      .replace(/\/$/, '')
      .trim();

    if (!/^[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/.test(cleanSlug)) {
      setScanError('Invalid format. Please specify the repository as "owner/repo" (e.g. "facebook/react" or "zeenat28-ui/greencode").');
      return;
    }

    setIsScanning(true);
    setScanError(null);
    try {
      const resp = await scanService.scanGitHub(cleanSlug, ghToken || undefined);
      const result = resp.data;
      result.is_github = true;
      result.repo_path = cleanSlug;
      result.energy_wh = result.energy_wh || estimateEnergy(result);
      result.carbon_g = result.carbon_g || estimateCarbon(result);
      setScanData(result);
      navigate('/dashboard');
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'GitHub scan failed. Make sure the repository exists and is accessible. For private repositories, configure a GitHub Personal Access Token in Settings.';
      setScanError(msg);
    } finally {
      setIsScanning(false);
    }
  };

  const isUploadScanning = uploadedFile.status === 'uploading' || uploadedFile.status === 'scanning';
  const isDisabled = isScanning || isUploadScanning;

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">Audit Codebase</h1>
        <p className="text-sm text-slate-500 mt-1">
          Perform Green Software Foundation static carbon intensity analysis across your codebase.
        </p>
      </div>

      {/* Grid telemetry badge */}
      {gridData && (
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-600 bg-white border border-slate-200/80 rounded-2xl px-4 py-3 shadow-xs">
          <span className="flex items-center gap-1.5 font-semibold text-slate-800">
            <span className={`w-2 h-2 rounded-full ${gridData.is_live ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
            {gridData.is_live ? 'Live Regional Telemetry' : 'Regional Baseline'}
          </span>
          <span className="text-slate-300">|</span>
          <span className="font-medium text-slate-700">{gridData.name} ({gridData.zone})</span>
          <span className="text-slate-300">|</span>
          <span>
            Carbon Intensity: <strong className="text-slate-900 font-bold">{gridData.marginal_carbon_intensity ?? gridData.carbon_intensity}</strong> gCO₂/kWh
          </span>
          <span className="text-slate-300">|</span>
          <span className="text-emerald-700 font-semibold">{gridData.clean_energy_percentage}% Clean</span>
        </div>
      )}

      {/* Error alert banner */}
      {scanError && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-2xl text-xs text-red-700 flex items-start gap-3 shadow-xs animate-in fade-in">
          <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />
          <div className="flex-1 leading-relaxed font-medium">{scanError}</div>
          <button onClick={() => setScanError(null)} className="text-red-400 hover:text-red-600">
            <X size={14} />
          </button>
        </div>
      )}

      {/* Tab selection */}
      <div className="grid grid-cols-3 gap-1.5 p-1.5 bg-slate-200/70 rounded-2xl">
        <TabButton
          label="Local Directory"
          icon={FolderOpen}
          isActive={selectedTab === 'local'}
          onClick={() => { setSelectedTab('local'); setScanError(null); }}
        />
        <TabButton
          label="GitHub Repo"
          icon={GitBranch}
          isActive={selectedTab === 'github'}
          onClick={() => { setSelectedTab('github'); setScanError(null); }}
        />
        <TabButton
          label="Upload ZIP"
          icon={Upload}
          isActive={selectedTab === 'upload'}
          onClick={() => { setSelectedTab('upload'); setScanError(null); }}
        />
      </div>

      {/* Tab Content Card */}
      <div className="card p-6 shadow-xs border-slate-200/80">
        {/* Local Tab */}
        {selectedTab === 'local' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Repository Directory Path
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder='e.g. "samples" or "C:/Users/.../my-project"'
                  className="input pl-3.5 pr-28 text-xs font-mono"
                  value={scanTarget}
                  onChange={(e) => setScanTarget(e.target.value)}
                  disabled={isDisabled}
                />
                <button
                  type="button"
                  onClick={() => setScanTarget('samples')}
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-xs font-semibold px-2.5 py-1 bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-lg hover:bg-emerald-100 transition-colors"
                >
                  Use Samples
                </button>
              </div>
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                Provide an absolute or relative directory path on this machine. GreenCode analyzes Python, TypeScript, JavaScript, C++, Java, and Go files without altering your working tree.
              </p>
            </div>

            {ghRepos.length > 0 && (
              <div>
                <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                  Or Scan One of Your GitHub Repositories
                </label>
                <select
                  className="input text-xs"
                  onChange={(e) => {
                    if (e.target.value) {
                      setScanTarget(e.target.value);
                      setSelectedTab('github');
                    }
                  }}
                  disabled={isDisabled}
                >
                  <option value="">Choose synced repository...</option>
                  {ghRepos.map((r: any) => (
                    <option key={r.id || r.full_name} value={r.full_name}>
                      {r.full_name} ({r.language || 'Code'})
                    </option>
                  ))}
                </select>
              </div>
            )}

            <button
              onClick={handleLocalScan}
              disabled={isDisabled}
              className="btn-primary flex items-center justify-center gap-2 w-full py-2.5 text-xs shadow-xs"
            >
              {isScanning ? (
                <>
                  <Loader2 size={15} className="animate-spin" /> Scanning AST &amp; Computing Carbon...
                </>
              ) : (
                <>
                  <Search size={15} /> Scan Local Repository
                </>
              )}
            </button>
          </div>
        )}

        {/* GitHub Tab */}
        {selectedTab === 'github' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                GitHub Repository Slug or URL
              </label>
              <input
                type="text"
                placeholder="e.g. owner/repo-name or https://github.com/owner/repo"
                className="input text-xs font-mono"
                value={scanTarget}
                onChange={(e) => setScanTarget(e.target.value)}
                disabled={isDisabled}
              />
              <p className="text-xs text-slate-500 mt-2 leading-relaxed">
                GreenCode downloads the remote code archive directly from the GitHub API, parses Concrete Syntax Trees, checks GSF compliance, and flags energy anti-patterns.
              </p>
            </div>

            {ghRepos.length > 0 && (
              <div>
                <label className="block text-xs font-semibold text-slate-600 mb-1.5">
                  Quick Select from Synced Repositories
                </label>
                <div className="flex flex-wrap gap-2">
                  {ghRepos.slice(0, 6).map((r: any) => (
                    <button
                      key={r.full_name}
                      type="button"
                      onClick={() => setScanTarget(r.full_name)}
                      className={`text-xs px-2.5 py-1 rounded-lg border font-medium transition-colors ${
                        scanTarget === r.full_name
                          ? 'bg-emerald-50 border-emerald-400 text-emerald-800 font-semibold'
                          : 'bg-slate-50 border-slate-200 text-slate-700 hover:bg-slate-100'
                      }`}
                    >
                      {r.name}
                    </button>
                  ))}
                </div>
              </div>
            )}

            <button
              onClick={handleGitHubScan}
              disabled={isDisabled}
              className="btn-primary flex items-center justify-center gap-2 w-full py-2.5 text-xs shadow-xs"
            >
              {isScanning ? (
                <>
                  <Loader2 size={15} className="animate-spin" /> Downloading &amp; Scanning GitHub Repo...
                </>
              ) : (
                <>
                  <GitBranch size={15} /> Scan GitHub Repository
                </>
              )}
            </button>
          </div>
        )}

        {/* Upload ZIP Tab */}
        {selectedTab === 'upload' && (
          <div className="space-y-5">
            <div>
              <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 mb-2">
                Source Code ZIP Archive
              </label>

              {!uploadedFile.file ? (
                <div
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-all duration-150 ${
                    isDragging
                      ? 'border-emerald-600 bg-emerald-50/50 scale-[1.01]'
                      : 'border-slate-300 hover:border-emerald-500 hover:bg-slate-50/70'
                  }`}
                >
                  <Upload size={38} className={`mx-auto mb-3 ${isDragging ? 'text-emerald-600' : 'text-slate-400'}`} />
                  <p className="font-semibold text-sm text-slate-800">
                    Click to browse or drag &amp; drop a ZIP file here
                  </p>
                  <p className="text-xs text-slate-400 mt-1">
                    Max size 50MB · Supports multi-language projects
                  </p>
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".zip"
                    onChange={handleZipUpload}
                    className="hidden"
                  />
                </div>
              ) : (
                <div className="card-inset p-4 flex items-center justify-between border-emerald-200 bg-emerald-50/20">
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                      <FileCode size={20} />
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-bold text-slate-800 truncate">
                        {uploadedFile.file.name}
                      </p>
                      <p className="text-xs text-slate-500">
                        {(uploadedFile.file.size / (1024 * 1024)).toFixed(2)} MB · Ready to scan
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => setUploadedFile({ file: null, progress: 0, status: 'idle' })}
                      disabled={isUploadScanning}
                      className="text-xs font-semibold text-slate-500 hover:text-slate-700 px-2.5 py-1 rounded-lg hover:bg-slate-200/50 transition-colors"
                    >
                      Change
                    </button>
                  </div>
                </div>
              )}
            </div>

            {uploadedFile.file && (
              <button
                onClick={handleUploadScan}
                disabled={isUploadScanning}
                className="btn-primary flex items-center justify-center gap-2 w-full py-2.5 text-xs shadow-xs"
              >
                {isUploadScanning ? (
                  <>
                    <Loader2 size={15} className="animate-spin" /> Uploading &amp; Auditing Archive...
                  </>
                ) : (
                  <>
                    <CheckCircle2 size={15} /> Audit Uploaded Archive
                  </>
                )}
              </button>
            )}
          </div>
        )}
      </div>

      {/* Progress Card when Scanning */}
      {isScanning && (
        <div className="card p-5 bg-emerald-50/30 border-emerald-200 shadow-xs animate-pulse">
          <div className="flex items-center gap-3 text-xs text-slate-700 font-medium">
            <Loader2 size={16} className="animate-spin text-emerald-600 shrink-0" />
            <span>Analyzing source code Concrete Syntax Trees against GSF SCI standards...</span>
          </div>
        </div>
      )}
    </div>
  );
}

function TabButton({ label, icon: Icon, isActive, onClick }: {
  label: string; icon: any; isActive: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center justify-center gap-2 px-3.5 py-2 rounded-xl font-semibold text-xs transition-all duration-150 ${
        isActive
          ? 'bg-white shadow-xs text-slate-900 font-bold'
          : 'text-slate-600 hover:text-slate-900 hover:bg-white/40'
      }`}
    >
      <Icon size={14} className={isActive ? 'text-emerald-600' : 'text-slate-400'} />
      {label}
    </button>
  );
}

