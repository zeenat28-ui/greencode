import { useState } from 'react';
import { scopeService, mlService, awsService } from '../services/greencodeApi';
import { Button } from '../components/primitives/Button';
import { Badge } from '../components/primitives/Badge';
import { Card } from '../components/primitives/Card';
import { Input } from '../components/primitives/Input';
import { Select } from '../components/primitives/Select';
import {
  Cpu,
  Cloud,
  FileCheck,
  Zap,
  Activity,
  RefreshCw,
  Sliders,
  Server,
  Link2,
  TrendingDown,
  ShieldCheck,
} from 'lucide-react';

type TabKey = 'scope' | 'ml_audit' | 'tokens' | 'aws';

export default function CloudCarbon() {
  const [activeTab, setActiveTab] = useState<TabKey>('scope');

  // Scope 1-3 Form State
  const [scopeForm, setScopeForm] = useState({
    energy_joules: 360000,
    duration_seconds: 3600,
    grid_intensity: 380,
    runs_per_year: 50000,
    team_size: 12,
    dev_hours: 160,
    cloud_provider: 'aws',
    vcpu_count: 8,
    memory_gb: 32,
    data_transfer_gb: 5.0,
    renewable_rec_pct: 0,
  });
  const [scopeResult, setScopeResult] = useState<any>(null);
  const [scopeLoading, setScopeLoading] = useState(false);

  // ML Code Audit State
  const [mlCode, setMlCode] = useState<string>(`import torch
import torchvision.models as models

# Unoptimized PyTorch inference pipeline running on AWS EC2
model = models.resnet50(pretrained=True)
model.eval()

def predict(input_tensor):
    # CRITICAL: Missing torch.no_grad() leads to memory graph retention
    output = model(input_tensor)
    
    # CRITICAL: Sync GPU-to-CPU tensor transfer inside critical path
    prediction = output.cpu().numpy()
    return prediction
`);
  const [mlAuditResult, setMlAuditResult] = useState<any>(null);
  const [mlAuditLoading, setMlAuditLoading] = useState(false);

  // Token Projections State
  const [tokenForm, setTokenForm] = useState({
    parameter_count_b: 7.0,
    token_count: 2048,
    hardware: 'h100',
    grid_intensity: 200,
    runs_per_year: 1000000,
  });
  const [tokenResult, setTokenResult] = useState<any>(null);
  const [tokenLoading, setTokenLoading] = useState(false);

  // ------------------------------------------------------------------
  // AWS FinOps & Carbon state (all values come from the live /api/aws/* API)
  // ------------------------------------------------------------------
  const [awsRegions, setAwsRegions] = useState<any>(null);
  const [awsCarbon, setAwsCarbon] = useState<any>(null);
  const [awsCarbonLoading, setAwsCarbonLoading] = useState(false);
  const [awsRegion, setAwsRegion] = useState('us-east-1');

  const [migrationForm, setMigrationForm] = useState({
    current_region: 'us-east-1',
    monthly_kwh: 1000,
    data_residency: 'GLOBAL',
  });
  const [migrationResult, setMigrationResult] = useState<any>(null);
  const [migrationLoading, setMigrationLoading] = useState(false);

  const [awsAccounts, setAwsAccounts] = useState<any[]>([]);
  const [linkForm, setLinkForm] = useState({
    account_id: '',
    role_arn: '',
    account_name: 'AWS Account',
    region: 'us-east-1',
  });
  const [linkLoading, setLinkLoading] = useState(false);
  const [linkMsg, setLinkMsg] = useState<string | null>(null);

  const [costCarbon, setCostCarbon] = useState<any>(null);
  const [costCarbonLoading, setCostCarbonLoading] = useState(false);
  const [costCarbonAccount, setCostCarbonAccount] = useState('');

  const handleRunScope = async () => {
    setScopeLoading(true);
    try {
      const resp = await scopeService.calculateInventory({
        energy_joules: Number(scopeForm.energy_joules),
        duration_seconds: Number(scopeForm.duration_seconds),
        grid_intensity_gco2_per_kwh: Number(scopeForm.grid_intensity),
        runs_per_year: Number(scopeForm.runs_per_year),
        team_size: Number(scopeForm.team_size),
        dev_hours: Number(scopeForm.dev_hours),
        cloud_provider: scopeForm.cloud_provider,
        vcpu_count: Number(scopeForm.vcpu_count),
        memory_gb: Number(scopeForm.memory_gb),
        data_transfer_gb: Number(scopeForm.data_transfer_gb),
        renewable_rec_pct: Number(scopeForm.renewable_rec_pct),
      });
      setScopeResult(resp.data);
    } catch (err) {
      console.error('Scope inventory calculation error:', err);
    } finally {
      setScopeLoading(false);
    }
  };

  const handleRunMlAudit = async () => {
    setMlAuditLoading(true);
    try {
      const resp = await mlService.auditCode(mlCode, 'inference_pipeline.py');
      setMlAuditResult(resp.data);
    } catch (err) {
      console.error('ML Audit error:', err);
    } finally {
      setMlAuditLoading(false);
    }
  };

  const handleRunTokenCalc = async () => {
    setTokenLoading(true);
    try {
      const resp = await mlService.calculateTokens({
        parameter_count_b: Number(tokenForm.parameter_count_b),
        token_count: Number(tokenForm.token_count),
        hardware: tokenForm.hardware,
        grid_intensity_gco2_per_kwh: Number(tokenForm.grid_intensity),
        runs_per_year: Number(tokenForm.runs_per_year),
      });
      setTokenResult(resp.data);
    } catch (err) {
      console.error('Token calculation error:', err);
    } finally {
      setTokenLoading(false);
    }
  };

  // ---- AWS FinOps & Carbon handlers (live /api/aws/* calls) ----
  const loadAwsRegions = async () => {
    try {
      const resp = await awsService.getRegions();
      setAwsRegions(resp.data);
      // Preselect the first supported region for the carbon lookup.
      const regions: string[] = resp.data?.regions || [];
      if (regions.length && !regions.includes(awsRegion)) setAwsRegion(regions[0]);
    } catch (err) {
      console.error('AWS regions load error:', err);
    }
  };

  const loadAwsCarbon = async (region: string) => {
    setAwsCarbonLoading(true);
    try {
      const resp = await awsService.getRegionCarbon(region);
      setAwsCarbon(resp.data);
    } catch (err) {
      console.error('AWS region carbon error:', err);
      setAwsCarbon(null);
    } finally {
      setAwsCarbonLoading(false);
    }
  };

  const loadAwsAccounts = async () => {
    try {
      const resp = await awsService.listAccounts();
      const accounts = resp.data?.accounts || [];
      setAwsAccounts(accounts);
      if (accounts.length && !costCarbonAccount) {
        setCostCarbonAccount(accounts[0].account_id);
      }
    } catch (err) {
      console.error('AWS accounts load error:', err);
    }
  };

  const handleLinkAccount = async () => {
    setLinkLoading(true);
    setLinkMsg(null);
    try {
      const resp = await awsService.linkAccount({
        account_id: linkForm.account_id.trim(),
        role_arn: linkForm.role_arn.trim(),
        account_name: linkForm.account_name.trim() || 'AWS Account',
        region: linkForm.region,
      });
      const data = resp.data;
      if (data?.status === 'LINKED') {
        setLinkMsg(`Linked ${data.account_name} (${data.account_id}) - STS session verified.`);
        setLinkForm({ account_id: '', role_arn: '', account_name: 'AWS Account', region: 'us-east-1' });
        loadAwsAccounts();
      } else {
        setLinkMsg(`Link failed: ${data?.error || data?.error_code || 'unknown error'}`);
      }
    } catch (err: any) {
      setLinkMsg(err?.response?.data?.detail || 'Link failed. Check the account ID and role ARN.');
    } finally {
      setLinkLoading(false);
    }
  };

  const handleUnlinkAccount = async (accountId: string) => {
    try {
      await awsService.unlinkAccount(accountId);
      loadAwsAccounts();
    } catch (err) {
      console.error('AWS unlink error:', err);
    }
  };

  const handleCostCarbon = async () => {
    if (!costCarbonAccount) return;
    setCostCarbonLoading(true);
    try {
      const resp = await awsService.getCostCarbon(costCarbonAccount);
      setCostCarbon(resp.data);
    } catch (err: any) {
      setCostCarbon(err?.response?.data?.detail ? { error: err.response.data.detail } : null);
      console.error('AWS cost-carbon error:', err);
    } finally {
      setCostCarbonLoading(false);
    }
  };

  const handleMigration = async () => {
    setMigrationLoading(true);
    try {
      const resp = await awsService.recommendMigration({
        current_region: migrationForm.current_region,
        monthly_kwh: Number(migrationForm.monthly_kwh),
        data_residency: migrationForm.data_residency,
      });
      setMigrationResult(resp.data);
    } catch (err) {
      console.error('AWS migration error:', err);
    } finally {
      setMigrationLoading(false);
    }
  };

  return (
    <div className="space-y-6 max-w-full overflow-hidden">
      {/* Enterprise Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1 border-b border-slate-200/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">Cloud &amp; AI Carbon Emissions</h1>
            <span className="badge bg-olive-100 text-olive-900 border border-olive-200">AWS &amp; GPU Profiler</span>
          </div>
          <p className="text-xs text-slate-500 mt-1">
            Measure cloud infrastructure emissions, compare AWS regions, and estimate GPU &amp; LLM model energy consumption.
          </p>
        </div>

        {/* Tab Controls */}
        <div className="inline-flex items-center p-1 bg-slate-100 rounded-lg border border-slate-200/80 text-xs font-medium">
          <button
            onClick={() => setActiveTab('scope')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'scope'
                ? 'bg-white text-slate-900 font-semibold shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            Cloud Emissions (Scope 1–3)
          </button>
          <button
            onClick={() => setActiveTab('ml_audit')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'ml_audit'
                ? 'bg-white text-slate-900 font-semibold shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            AI &amp; GPU Model Auditor
          </button>
          <button
            onClick={() => setActiveTab('tokens')}
            className={`px-3 py-1.5 rounded-md transition-all ${
              activeTab === 'tokens'
                ? 'bg-white text-slate-900 font-semibold shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            LLM Token Energy Calculator
          </button>
          <button
            onClick={() => {
              setActiveTab('aws');
              if (!awsRegions) loadAwsRegions();
              if (awsAccounts.length === 0) loadAwsAccounts();
            }}
            className={`px-3 py-1.5 rounded-md transition-all flex items-center gap-1.5 ${
              activeTab === 'aws'
                ? 'bg-white text-slate-900 font-semibold shadow-sm'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            <Server size={13} />
            AWS FinOps &amp; Carbon
          </button>
        </div>
      </div>

      {/* TAB 1: SCOPE 1-3 GHG INVENTORY */}
      {activeTab === 'scope' && (
        <div className="grid lg:grid-cols-12 gap-6 max-w-full overflow-hidden">
          <div className="lg:col-span-5">
            <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Sliders size={16} className="text-slate-500" />
                Infrastructure Parameters
              </h2>
              <span className="text-[11px] font-mono text-slate-400">AWS Datacenter PUE 1.15</span>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div>
                <label className="label block mb-1">Cloud Provider</label>
                <Select
                  value={scopeForm.cloud_provider}
                  onChange={(e) => setScopeForm({ ...scopeForm, cloud_provider: e.target.value })}
                  className="text-xs font-mono"
                >
                  <option value="aws">Amazon Web Services (AWS)</option>
                  <option value="gcp">Google Cloud Platform (GCP)</option>
                  <option value="azure">Microsoft Azure</option>
                </Select>
              </div>

              <div>
                <label className="label block mb-1">vCPU Allocation</label>
                <Input
                  type="number"
                  value={scopeForm.vcpu_count}
                  onChange={(e) => setScopeForm({ ...scopeForm, vcpu_count: Number(e.target.value) })}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Grid Intensity (gCO₂e/kWh)</label>
                <Input
                  type="number"
                  value={scopeForm.grid_intensity}
                  onChange={(e) => setScopeForm({ ...scopeForm, grid_intensity: Number(e.target.value) })}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Annual Runs / Invocations</label>
                <Input
                  type="number"
                  value={scopeForm.runs_per_year}
                  onChange={(e) => setScopeForm({ ...scopeForm, runs_per_year: Number(e.target.value) })}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Egress Data Transfer (GB)</label>
                <Input
                  type="number"
                  value={scopeForm.data_transfer_gb}
                  onChange={(e) => setScopeForm({ ...scopeForm, data_transfer_gb: Number(e.target.value) })}
                  className="text-xs font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Dev Team Size (FTE)</label>
                <Input
                  type="number"
                  value={scopeForm.team_size}
                  onChange={(e) => setScopeForm({ ...scopeForm, team_size: Number(e.target.value) })}
                  className="text-xs font-mono"
                />
              </div>
            </div>

            <Button
              onClick={handleRunScope}
              disabled={scopeLoading}
              variant="primary"
              className="w-full py-2.5 text-xs font-semibold"
            >
              {scopeLoading ? <RefreshCw size={14} className="animate-spin" /> : <FileCheck size={14} />}
              Compute Audit-Ready GHG Inventory
            </Button>
          </Card>
        </div>

        <div className="lg:col-span-7 space-y-4">
             {scopeResult ? (
               <div className="space-y-4">
                 <div className="grid sm:grid-cols-3 gap-3">
                    <Card className="border-l-4 border-l-slate-400 p-4">
                      <p className="label">Scope 1 (Direct)</p>
                     <p className="text-xl font-bold font-mono text-slate-900 mt-1">
                       {scopeResult.scope_1.total_emissions_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                     </p>
                     <p className="text-[11px] text-slate-500 mt-1">Development Team Overhead</p>
                   </Card>

                <Card className="border-l-4 border-l-emerald-600 p-4">
                     <p className="label">Scope 2 (Electricity)</p>
                     <p className="text-xl font-bold font-mono text-emerald-700 mt-1">
                       {scopeResult.scope_2.location_based_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                     </p>
                     <p className="text-[11px] text-slate-500 mt-1">AWS Compute Grid Footprint</p>
                   </Card>

                  <Card className="border-l-4 border-l-cyan-600 p-4">
                      <p className="label">Scope 3 (Supply Chain)</p>
                     <p className="text-xl font-bold font-mono text-cyan-800 mt-1">
                       {scopeResult.scope_3.total_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                     </p>
                     <p className="text-[11px] text-slate-500 mt-1">Hardware LCA &amp; Data Egress</p>
                   </Card>
                </div>

                <Card padding="lg">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      Organizational Carbon Breakdown
                    </h3>
                    <Badge variant="success">
                      Total: {scopeResult.total_organizational_carbon_kg_co2e.toFixed(2)} kg CO₂e / yr
                </Badge>
                </div>

                <div className="space-y-2.5 text-xs">
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-600">AWS Datacenter PUE Coefficient</span>
                    <span className="font-mono font-semibold">{scopeResult.cloud_pue}</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-600">Operational Energy Consumption</span>
                    <span className="font-mono font-semibold">{scopeResult.scope_2.annual_energy_kwh.toFixed(2)} kWh / year</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-600">Hardware Manufacturing LCA Amortization</span>
                    <span className="font-mono font-semibold">{scopeResult.scope_3.hardware_embodied_kg_co2e.toFixed(2)} kg CO₂e</span>
                  </div>
                  <div className="flex justify-between py-1 border-b border-slate-100">
                    <span className="text-slate-600">Regulatory Framework Compliance</span>
                    <span className="font-medium text-emerald-700">CSRD ESRS-E1 &middot; GHG Protocol &middot; SBTi ICT</span>
                  </div>
                </div>
              </Card>
              </div>
            ) : (
              <Card padding="none" className="p-12 text-center text-slate-500 space-y-3">
                <Cloud size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">No Inventory Generated</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click &ldquo;Compute Audit-Ready GHG Inventory&rdquo; to calculate certified Scope 1, Scope 2, and Scope 3 enterprise carbon metrics.
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: AI/ML WORKLOAD AUDITOR */}
      {activeTab === 'ml_audit' && (
        <div className="grid lg:grid-cols-12 gap-6 max-w-full overflow-hidden">
          <div className="lg:col-span-6 card p-5 space-y-3">
            <div className="flex items-center justify-between pb-2 border-b border-slate-100">
              <h2 className="text-xs font-bold text-slate-900 uppercase tracking-wider flex items-center gap-1.5">
                <Cpu size={14} className="text-slate-600" />
                PyTorch / Transformers Source Code
              </h2>
              <span className="text-[10px] font-mono text-slate-400">AST Pattern Detection</span>
            </div>

            <textarea
              value={mlCode}
              onChange={(e) => setMlCode(e.target.value)}
              rows={14}
              className="w-full p-3 font-mono text-xs bg-slate-900 text-slate-100 rounded-lg border border-slate-800 focus:outline-none focus:ring-1 focus:ring-slate-700"
              spellCheck={false}
            />

            <button
              onClick={handleRunMlAudit}
              disabled={mlAuditLoading}
              className="btn-primary w-full py-2.5 text-xs font-semibold flex items-center justify-center gap-2"
            >
              {mlAuditLoading ? <RefreshCw size={14} className="animate-spin" /> : <Activity size={14} />}
              Scan for AI &amp; GPU Energy Anti-Patterns
            </button>
          </div>

          <div className="lg:col-span-6 space-y-4">
        {mlAuditResult ? (
          <div className="space-y-3">
            <Card padding="lg" className="flex items-center justify-between">
              <div>
                <p className="label">AI Workload Status</p>
                <p className="text-lg font-bold text-slate-900 mt-0.5">
                  {mlAuditResult.detected_patterns.length} Inefficiencies Detected
                </p>
              </div>
              <Badge variant={mlAuditResult.detected_patterns.length > 0 ? 'critical' : 'success'}>
                {mlAuditResult.detected_patterns.length > 0 ? 'GPU Optimization Required' : 'Optimal'}
              </Badge>
            </Card>

                <div className="space-y-2.5">
                  {mlAuditResult.detected_patterns.map((p: any, idx: number) => (
                    <Card key={idx} className="border-l-4 border-l-amber-500 p-4 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold font-mono text-slate-900">{p.rule_id}</span>
                        <Badge variant="high" size="sm" className="text-[10px]">{p.severity}</Badge>
                      </div>
                      <p className="text-xs font-semibold text-slate-800">{p.title}</p>
                      <p className="text-[11px] text-slate-600">{p.description}</p>
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                        <span className="text-slate-500 font-mono">Line {p.line_number}</span>
                        <span className="text-emerald-700 font-medium">Estimated savings: {p.estimated_energy_savings_pct}% Joules</span>
                </div>
              </Card>
                  ))}
                </div>
              </div>
            ) : (
              <Card padding="none" className="p-12 text-center text-slate-500 space-y-3">
                <Cpu size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">Awaiting ML Workload Scan</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click &ldquo;Scan for AI &amp; GPU Energy Anti-Patterns&rdquo; to analyze the Python model for unquantized inference, missing KV-cache, and GPU sync bottlenecks.
                </p>
              </Card>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: LLM TOKEN ENERGY MODELING */}
      {activeTab === 'tokens' && (
        <div className="grid lg:grid-cols-12 gap-6 max-w-full overflow-hidden">
            <div className="lg:col-span-5">
            <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Zap size={16} className="text-slate-500" />
                Inference Specifications
              </h2>
              <span className="text-[11px] font-mono text-slate-400">Tokens &middot; Joules &middot; Hardware</span>
            </div>

            <div className="space-y-3 text-xs">
              <div>
                <label className="label block mb-1">Model Parameters</label>
                <Select
                  value={tokenForm.parameter_count_b}
                  onChange={(e) => setTokenForm({ ...tokenForm, parameter_count_b: Number(e.target.value) })}
                  className="text-xs font-mono"
                >
                  <option value={7.0}>7 Billion Parameters (Llama-3-8B / Mistral-7B)</option>
                  <option value={13.0}>13 Billion Parameters (Standard Mid-tier)</option>
                  <option value={70.0}>70 Billion Parameters (Llama-3-70B / Enterprise)</option>
                  <option value={405.0}>405 Billion Parameters (Frontier Scale)</option>
                </Select>
              </div>

              <div>
                <label className="label block mb-1">Target Accelerator Hardware</label>
                <Select
                  value={tokenForm.hardware}
                  onChange={(e) => setTokenForm({ ...tokenForm, hardware: e.target.value })}
                  className="text-xs font-mono"
                >
                  <option value="aws_inferentia2">AWS Inferentia2 (inf2 &middot; 190W TDP &middot; BF16/FP8 NeuronCore-v2)</option>
                  <option value="aws_trainium">AWS Trainium1 (trn1 &middot; 500W TDP &middot; High-Efficiency Training)</option>
                  <option value="aws_graviton4">AWS Graviton4 (c8g/r8g &middot; 130W TDP &middot; ARM Neoverse-V2)</option>
                  <option value="h100">NVIDIA H100 SXM5 (700W TDP &middot; FP8 Engine)</option>
                  <option value="a100">NVIDIA A100 80GB (400W TDP &middot; Standard Cloud)</option>
                  <option value="rtx_4090">NVIDIA RTX 4090 (450W TDP &middot; Edge Workstation)</option>
                  <option value="cpu">x86_64 Datacenter CPU (Xeon / EPYC)</option>
                  <option value="npu">Dedicated NPU / Apple Neural Engine</option>
                </Select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label block mb-1">Tokens / Request</label>
                  <Input
                    type="number"
                    value={tokenForm.token_count}
                    onChange={(e) => setTokenForm({ ...tokenForm, token_count: Number(e.target.value) })}
                    className="text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="label block mb-1">Grid Intensity (g/kWh)</label>
                  <Input
                    type="number"
                    value={tokenForm.grid_intensity}
                    onChange={(e) => setTokenForm({ ...tokenForm, grid_intensity: Number(e.target.value) })}
                    className="text-xs font-mono"
                  />
                </div>
              </div>
            </div>

            <Button
              onClick={handleRunTokenCalc}
              disabled={tokenLoading}
              variant="primary"
              className="w-full py-2.5 text-xs font-semibold"
            >
              {tokenLoading ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
              Model Token Energy &amp; Carbon Impact
            </Button>
            </Card>
          </div>

            <div className="lg:col-span-7 space-y-4">
             {tokenResult ? (
              <div className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-3">
                  <Card className="p-4">
                    <p className="label">Inference Energy</p>
                    <p className="text-xl font-bold font-mono text-slate-900 mt-1">
                      {tokenResult.joules_per_run.toFixed(3)} <span className="text-xs text-slate-500 font-normal">Joules</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {(tokenResult.joules_per_run / 3600).toFixed(6)} Wh per {tokenForm.token_count} tokens
                    </p>
                  </Card>

                  <Card className="p-4">
                    <p className="label">Inference Carbon</p>
                    <p className="text-xl font-bold font-mono text-emerald-700 mt-1">
                      {tokenResult.gco2e_per_run.toFixed(6)} <span className="text-xs text-slate-500 font-normal">gCO₂e</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Direct operational footprint</p>
                  </Card>
                </div>

                <Card padding="lg" className="space-y-3">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800 pb-2 border-b border-slate-100">
                    Annual Scale Projection (1M Invocations)
                  </h3>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <p className="text-slate-500">Annual Energy Demand</p>
                      <p className="font-mono text-sm font-bold text-slate-900 mt-0.5">
                        {tokenResult.annual_energy_kwh.toFixed(2)} kWh
                      </p>
                    </div>
                    <div>
                      <p className="text-slate-500">Annual Atmospheric Carbon</p>
                      <p className="font-mono text-sm font-bold text-emerald-700 mt-0.5">
                        {tokenResult.annual_carbon_kg.toFixed(2)} kg CO₂e
                      </p>
                    </div>
                  </div>
                  {tokenResult.aws_silicon_recommendation && (
                    <div className="mt-3 p-3 rounded-lg bg-amber-50 border border-amber-200 text-xs text-amber-950">
                      <span className="font-bold">AWS Native Silicon Advisory: </span>
                      {tokenResult.aws_silicon_recommendation}
                    </div>
                  )}
                  </Card>
                </div>
              ) : (
            <Card padding="none" className="p-12 text-center text-slate-500 space-y-3">
              <Zap size={36} className="mx-auto text-slate-300" />
              <p className="text-sm font-semibold text-slate-700">Token Model Uncomputed</p>
              <p className="text-xs text-slate-400 max-w-sm mx-auto">
                Simulate energy consumption across AWS Inferentia2, Trainium, Graviton4, and NVIDIA H100/A100 architectures.
              </p>
            </Card>
          )}
        </div>
      </div>
      )}

      {/* TAB 4: AWS FinOps & Carbon - every value is a live /api/aws/* response */}
      {activeTab === 'aws' && (
        <div className="space-y-6">
          {/* Row A: Region carbon intensity + migration advisor */}
          <div className="grid lg:grid-cols-12 gap-6">
            {/* Region carbon intensity */}
            <div className="lg:col-span-5">
            <Card padding="lg" className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Cloud size={16} className="text-slate-500" />
                  Regional Grid Carbon Intensity
                </h2>
              </div>
              <div>
                <label className="label block mb-1">AWS Region</label>
                <div className="flex gap-2">
                  <Select
                    value={awsRegion}
                    onChange={(e) => setAwsRegion(e.target.value)}
                    className="text-xs font-mono flex-1"
                  >
                    {(awsRegions?.regions || ['us-east-1', 'eu-west-1', 'eu-north-1']).map((r: string) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </Select>
                  <Button
                    onClick={() => loadAwsCarbon(awsRegion)}
                    disabled={awsCarbonLoading}
                    variant="secondary"
                    size="sm"
                    className="text-xs"
                  >
                    {awsCarbonLoading ? <RefreshCw size={13} className="animate-spin" /> : <Activity size={13} />}
                    Resolve
                  </Button>
                </div>
              </div>

              {awsCarbon ? (
                <div className="space-y-2">
                  <div className="flex items-baseline gap-2">
                    <span className="text-3xl font-bold font-mono text-slate-900">
                      {Number(awsCarbon.carbon_intensity ?? 0).toFixed(1)}
                    </span>
                    <span className="text-xs text-slate-500">gCO₂eq/kWh</span>
                  </div>
                  <div className="text-[11px] font-mono text-slate-500 space-y-0.5">
                    <div>Grid zone: <span className="text-slate-700">{awsCarbon.grid_zone}</span></div>
                    <div>Source: <span className="text-slate-700">{awsCarbon.source}</span> · tier <span className="text-slate-700">{awsCarbon.tier}</span></div>
                    {awsCarbon.citation && <div className="text-slate-400">{awsCarbon.citation}</div>}
                  </div>
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  Select a region and press Resolve to read live grid intensity (Electricity Maps) or the cited Ember 2024 reference.
                </p>
              )}
            </Card>
            </div>
            {/* Migration advisor */}
            <div className="lg:col-span-7">
            <Card padding="lg" className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <TrendingDown size={16} className="text-slate-500" />
                  Carbon-Optimal Region Migration
                </h2>
              </div>
              <div className="grid grid-cols-3 gap-3 text-xs">
                <div>
                  <label className="label block mb-1">Current Region</label>
                  <Select
                    value={migrationForm.current_region}
                    onChange={(e) => setMigrationForm({ ...migrationForm, current_region: e.target.value })}
                    className="text-xs font-mono"
                  >
                    {(awsRegions?.regions || ['us-east-1']).map((r: string) => (
                      <option key={r} value={r}>{r}</option>
                    ))}
                  </Select>
                </div>
                <div>
                  <label className="label block mb-1">Monthly kWh</label>
                  <Input
                    type="number"
                    value={migrationForm.monthly_kwh}
                    onChange={(e) => setMigrationForm({ ...migrationForm, monthly_kwh: Number(e.target.value) })}
                    className="text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="label block mb-1">Data Residency</label>
                  <Select
                    value={migrationForm.data_residency}
                    onChange={(e) => setMigrationForm({ ...migrationForm, data_residency: e.target.value })}
                    className="text-xs font-mono"
                  >
                    <option value="GLOBAL">Global</option>
                    <option value="EU_STRICT">EU only</option>
                    <option value="US_STRICT">US/CA only</option>
                    <option value="APAC_STRICT">APAC only</option>
                  </Select>
                </div>
              </div>
              <Button
                onClick={handleMigration}
                disabled={migrationLoading}
                variant="primary"
                className="w-full py-2 text-xs font-semibold"
              >
                {migrationLoading ? <RefreshCw size={14} className="animate-spin" /> : <TrendingDown size={14} />}
                Rank Cleaner Regions
              </Button>

              {migrationResult && (
                <div className="space-y-2">
                  <div className="flex flex-wrap items-center gap-2 text-xs">
                    <span className="font-mono text-slate-500">Recommended:</span>
                    <span className="font-mono font-bold text-emerald-700">{migrationResult.recommended_region}</span>
                    {Number(migrationResult.max_carbon_reduction_pct) > 0 && (
                      <Badge variant="success">
                        -{Number(migrationResult.max_carbon_reduction_pct).toFixed(1)}% · {Number(migrationResult.max_annual_co2_saved_kg).toFixed(1)} kg CO₂e/yr
                      </Badge>
                    )}
                  </div>
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-[11px] font-mono">
                      <thead className="text-slate-400 border-b border-slate-100">
                        <tr>
                          <th className="py-1.5 pr-3">Region</th>
                          <th className="py-1.5 pr-3">gCO₂/kWh</th>
                          <th className="py-1.5 pr-3">Reduction</th>
                          <th className="py-1.5 pr-3">Annual Saved</th>
                          <th className="py-1.5">Latency</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-50">
                        {(migrationResult.candidates || []).map((c: any) => (
                          <tr key={c.region}>
                            <td className="py-1.5 pr-3 text-slate-800">{c.region}</td>
                            <td className="py-1.5 pr-3 text-slate-600">{Number(c.carbon_intensity_gco2_kwh).toFixed(1)}</td>
                            <td className="py-1.5 pr-3 text-emerald-700">{Number(c.carbon_reduction_pct).toFixed(1)}%</td>
                            <td className="py-1.5 pr-3 text-slate-600">{Number(c.annual_co2_saved_kg).toFixed(1)} kg</td>
                            <td className="py-1.5 text-slate-400">{c.latency_impact}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </Card>
            </div>
          </div>
            {/* Row B: Link account form + linked accounts list */}
            <div className="grid lg:grid-cols-12 gap-6">
            {/* Link account form */}
            <div className="lg:col-span-5">
            <Card padding="lg" className="space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <Link2 size={16} className="text-slate-500" />
                  Link AWS Account (STS AssumeRole)
                </h2>
              </div>
              <p className="text-[11px] text-slate-500 leading-relaxed">
                GreenCode assumes a read-only role in your account. Temporary STS credentials are used for the
                call and are never stored or returned.
              </p>
              <div className="space-y-2.5 text-xs">
                <div>
                  <label className="label block mb-1">Account ID (12 digits)</label>
                  <Input
                    value={linkForm.account_id}
                    onChange={(e) => setLinkForm({ ...linkForm, account_id: e.target.value })}
                    placeholder="123456789012"
                    className="text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="label block mb-1">Role ARN</label>
                  <Input
                    value={linkForm.role_arn}
                    onChange={(e) => setLinkForm({ ...linkForm, role_arn: e.target.value })}
                    placeholder="arn:aws:iam::123456789012:role/GreenCodeReadOnly"
                    className="text-xs font-mono"
                  />
                </div>
                <div className="grid grid-cols-2 gap-2">
                  <div>
                    <label className="label block mb-1">Name</label>
                    <Input
                      value={linkForm.account_name}
                      onChange={(e) => setLinkForm({ ...linkForm, account_name: e.target.value })}
                      className="text-xs"
                    />
                  </div>
                  <div>
                    <label className="label block mb-1">Region</label>
                    <Select
                      value={linkForm.region}
                      onChange={(e) => setLinkForm({ ...linkForm, region: e.target.value })}
                      className="text-xs font-mono"
                    >
                      {(awsRegions?.regions || ['us-east-1']).map((r: string) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </Select>
                  </div>
                </div>
              </div>
              <Button
                onClick={handleLinkAccount}
                disabled={linkLoading || !linkForm.account_id.trim() || !linkForm.role_arn.trim()}
                variant="primary"
                className="w-full py-2 text-xs font-semibold"
              >
                {linkLoading ? <RefreshCw size={14} className="animate-spin" /> : <Link2 size={14} />}
                Link Account
              </Button>
              {linkMsg && (
                <p className={`text-[11px] font-mono ${linkMsg.startsWith('Linked') ? 'text-emerald-700' : 'text-rose-700'}`}>
                  {linkMsg}
                </p>
              )}
            </Card>
            </div>
            {/* Linked accounts list */}
            <div className="lg:col-span-7">
            <Card padding="lg" className="space-y-3">
              <div className="flex items-center justify-between pb-3 border-b border-slate-100">
                <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                  <ShieldCheck size={16} className="text-slate-500" />
                  Linked Accounts ({awsAccounts.length})
                </h2>
                <Button onClick={loadAwsAccounts} variant="ghost" size="sm" className="text-[11px]">
                  <RefreshCw size={12} /> Refresh
                </Button>
              </div>
              {awsAccounts.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="text-slate-400 border-b border-slate-100">
                      <tr>
                        <th className="py-2 pr-3 font-medium">Account</th>
                        <th className="py-2 pr-3 font-medium">ID</th>
                        <th className="py-2 pr-3 font-medium">Region</th>
                        <th className="py-2 pr-3 font-medium">Status</th>
                        <th className="py-2 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-50">
                      {awsAccounts.map((a) => (
                        <tr key={a.account_id}>
                          <td className="py-2 pr-3 text-slate-800 font-medium">{a.account_name}</td>
                          <td className="py-2 pr-3 font-mono text-slate-600">{a.account_id}</td>
                          <td className="py-2 pr-3 font-mono text-slate-600">{a.region}</td>
                          <td className="py-2 pr-3">
                            <Badge variant="success">{a.status}</Badge>
                          </td>
                            <td className="py-2 text-right space-x-1">
                              <Button
                                onClick={() => setCostCarbonAccount(a.account_id)}
                                variant="ghost"
                                size="xs"
                                className="text-[11px]"
                              >
                                Cost &amp; Carbon
                              </Button>
                              <Button
                                onClick={() => handleUnlinkAccount(a.account_id)}
                                variant="ghost-danger"
                                size="xs"
                                className="text-[11px]"
                              >
                                Unlink
                              </Button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p className="text-xs text-slate-400">
                  No AWS accounts linked yet. Link one to read live AWS Budgets spend and calibrated carbon.
                </p>
              )}
            </Card>
          </div>
          </div>
          {/* Row C: Month-to-date cost & carbon for the selected account */}
          <Card padding="lg" className="space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h2 className="text-sm font-bold text-slate-900 flex items-center gap-2">
                <Server size={16} className="text-slate-500" />
                Month-to-Date Cost &amp; Carbon
              </h2>
              <div className="flex items-center gap-2">
                <Select
                  value={costCarbonAccount}
                  onChange={(e) => setCostCarbonAccount(e.target.value)}
                  className="text-xs font-mono"
                >
                  <option value="">Select account…</option>
                  {awsAccounts.map((a) => (
                    <option key={a.account_id} value={a.account_id}>{a.account_name} ({a.account_id})</option>
                  ))}
                </Select>
                <Button
                  onClick={handleCostCarbon}
                  disabled={costCarbonLoading || !costCarbonAccount}
                  variant="secondary"
                  size="sm"
                  className="text-xs"
                >
                  {costCarbonLoading ? <RefreshCw size={13} className="animate-spin" /> : <Activity size={13} />}
                  Fetch
                </Button>
              </div>
            </div>

            {costCarbon?.error ? (
              <p className="text-xs text-rose-700 font-mono">{costCarbon.error}</p>
            ) : costCarbon ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <Card variant="inset" padding="md">
                  <p className="label">MTD Spend (AWS Budgets)</p>
                  <p className="text-xl font-bold font-mono text-slate-900 mt-1">${Number(costCarbon.cost_usd ?? 0).toFixed(2)}</p>
                  <p className="text-[11px] text-slate-500 mt-1">source: {costCarbon.cost_source} · {costCarbon.cost_tier}</p>
                </Card>
                <Card variant="inset" padding="md">
                  <p className="label">Grid Intensity</p>
                  <p className="text-xl font-bold font-mono text-slate-900 mt-1">{Number(costCarbon.carbon_intensity_gco2_kwh ?? 0).toFixed(1)}</p>
                  <p className="text-[11px] text-slate-500 mt-1">gCO₂/kWh · {costCarbon.grid_zone} · {costCarbon.carbon_tier}</p>
                </Card>
                <Card variant="inset" padding="md">
                  <p className="label">Calibrated Energy</p>
                  <p className="text-xl font-bold font-mono text-slate-900 mt-1">{Number(costCarbon.estimated_energy_kwh ?? 0).toFixed(2)}</p>
                  <p className="text-[11px] text-slate-500 mt-1">kWh · {costCarbon.instance_type} @ {costCarbon.region}</p>
                </Card>
                <Card variant="inset" padding="md">
                  <p className="label">Estimated CO₂e</p>
                  <p className="text-xl font-bold font-mono text-emerald-700 mt-1">{Number(costCarbon.estimated_co2e_kg ?? 0).toFixed(3)}</p>
                  <p className="text-[11px] text-slate-500 mt-1">kg CO₂e · {costCarbon.period_start} → {costCarbon.period_end}</p>
                </Card>
              </div>
            ) : (
              <p className="text-xs text-slate-400">
                Select a linked account and press Fetch to read month-to-date AWS Budgets spend and its physics-calibrated carbon footprint.
              </p>
            )}
          </Card>
        </div>
      )}
     </div>
  );
}

