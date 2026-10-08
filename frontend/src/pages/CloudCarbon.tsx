import { useState } from 'react';
import { scopeService, mlService } from '../services/greencodeApi';
import {
  Cpu,
  Cloud,
  FileCheck,
  Zap,
  Activity,
  Layers,
  Sparkles,
  Server,
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Database
} from 'lucide-react';

export default function CloudCarbon() {
  const [activeTab, setActiveTab] = useState<'scope' | 'ml_audit' | 'tokens'>('scope');

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
        </div>
      </div>

      {/* TAB 1: SCOPE 1-3 GHG INVENTORY */}
      {activeTab === 'scope' && (
        <div className="grid lg:grid-cols-12 gap-6 max-w-full overflow-hidden">
          <div className="lg:col-span-5 card p-5 space-y-4">
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
                <select
                  value={scopeForm.cloud_provider}
                  onChange={(e) => setScopeForm({ ...scopeForm, cloud_provider: e.target.value })}
                  className="input py-1.5"
                >
                  <option value="aws">Amazon Web Services (AWS)</option>
                  <option value="gcp">Google Cloud Platform (GCP)</option>
                  <option value="azure">Microsoft Azure</option>
                </select>
              </div>

              <div>
                <label className="label block mb-1">vCPU Allocation</label>
                <input
                  type="number"
                  value={scopeForm.vcpu_count}
                  onChange={(e) => setScopeForm({ ...scopeForm, vcpu_count: Number(e.target.value) })}
                  className="input py-1.5 font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Grid Intensity (gCO₂e/kWh)</label>
                <input
                  type="number"
                  value={scopeForm.grid_intensity}
                  onChange={(e) => setScopeForm({ ...scopeForm, grid_intensity: Number(e.target.value) })}
                  className="input py-1.5 font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Annual Runs / Invocations</label>
                <input
                  type="number"
                  value={scopeForm.runs_per_year}
                  onChange={(e) => setScopeForm({ ...scopeForm, runs_per_year: Number(e.target.value) })}
                  className="input py-1.5 font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Egress Data Transfer (GB)</label>
                <input
                  type="number"
                  value={scopeForm.data_transfer_gb}
                  onChange={(e) => setScopeForm({ ...scopeForm, data_transfer_gb: Number(e.target.value) })}
                  className="input py-1.5 font-mono"
                />
              </div>

              <div>
                <label className="label block mb-1">Dev Team Size (FTE)</label>
                <input
                  type="number"
                  value={scopeForm.team_size}
                  onChange={(e) => setScopeForm({ ...scopeForm, team_size: Number(e.target.value) })}
                  className="input py-1.5 font-mono"
                />
              </div>
            </div>

            <button
              onClick={handleRunScope}
              disabled={scopeLoading}
              className="btn-primary w-full py-2.5 text-xs font-semibold flex items-center justify-center gap-2"
            >
              {scopeLoading ? <RefreshCw size={14} className="animate-spin" /> : <FileCheck size={14} />}
              Compute Audit-Ready GHG Inventory
            </button>
          </div>

          <div className="lg:col-span-7 space-y-4">
            {scopeResult ? (
              <div className="space-y-4">
                <div className="grid sm:grid-cols-3 gap-3">
                  <div className="card p-4 border-l-4 border-l-slate-400">
                    <p className="label">Scope 1 (Direct)</p>
                    <p className="text-xl font-bold font-mono text-slate-900 mt-1">
                      {scopeResult.scope_1.total_emissions_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Development Team Overhead</p>
                  </div>

                  <div className="card p-4 border-l-4 border-l-emerald-600">
                    <p className="label">Scope 2 (Electricity)</p>
                    <p className="text-xl font-bold font-mono text-emerald-700 mt-1">
                      {scopeResult.scope_2.location_based_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">AWS Compute Grid Footprint</p>
                  </div>

                  <div className="card p-4 border-l-4 border-l-cyan-600">
                    <p className="label">Scope 3 (Supply Chain)</p>
                    <p className="text-xl font-bold font-mono text-cyan-800 mt-1">
                      {scopeResult.scope_3.total_kg_co2e.toFixed(2)} <span className="text-xs text-slate-500 font-normal">kg CO₂e</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Hardware LCA &amp; Data Egress</p>
                  </div>
                </div>

                <div className="card p-5">
                  <div className="flex items-center justify-between pb-3 border-b border-slate-100 mb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-800">
                      Organizational Carbon Breakdown
                    </h3>
                    <span className="badge bg-emerald-50 text-emerald-700 border border-emerald-200">
                      Total: {scopeResult.total_organizational_carbon_kg_co2e.toFixed(2)} kg CO₂e / yr
                    </span>
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
                </div>
              </div>
            ) : (
              <div className="card p-12 text-center text-slate-500 space-y-3">
                <Cloud size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">No Inventory Generated</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click &ldquo;Compute Audit-Ready GHG Inventory&rdquo; to calculate certified Scope 1, Scope 2, and Scope 3 enterprise carbon metrics.
                </p>
              </div>
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
                <div className="card p-4 flex items-center justify-between">
                  <div>
                    <p className="label">AI Workload Status</p>
                    <p className="text-lg font-bold text-slate-900 mt-0.5">
                      {mlAuditResult.detected_patterns.length} Inefficiencies Detected
                    </p>
                  </div>
                  <span className={`badge ${mlAuditResult.detected_patterns.length > 0 ? 'badge-critical' : 'badge-pass'}`}>
                    {mlAuditResult.detected_patterns.length > 0 ? 'GPU Optimization Required' : 'Optimal'}
                  </span>
                </div>

                <div className="space-y-2.5">
                  {mlAuditResult.detected_patterns.map((p: any, idx: number) => (
                    <div key={idx} className="card p-4 border-l-4 border-l-amber-500 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-bold font-mono text-slate-900">{p.rule_id}</span>
                        <span className="badge badge-high text-[10px]">{p.severity}</span>
                      </div>
                      <p className="text-xs font-semibold text-slate-800">{p.title}</p>
                      <p className="text-[11px] text-slate-600">{p.description}</p>
                      <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px]">
                        <span className="text-slate-500 font-mono">Line {p.line_number}</span>
                        <span className="text-emerald-700 font-medium">Estimated savings: {p.estimated_energy_savings_pct}% Joules</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <div className="card p-12 text-center text-slate-500 space-y-3">
                <Cpu size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">Awaiting ML Workload Scan</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Click &ldquo;Scan for AI &amp; GPU Energy Anti-Patterns&rdquo; to analyze the Python model for unquantized inference, missing KV-cache, and GPU sync bottlenecks.
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: LLM TOKEN ENERGY MODELING */}
      {activeTab === 'tokens' && (
        <div className="grid lg:grid-cols-12 gap-6 max-w-full overflow-hidden">
          <div className="lg:col-span-5 card p-5 space-y-4">
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
                <select
                  value={tokenForm.parameter_count_b}
                  onChange={(e) => setTokenForm({ ...tokenForm, parameter_count_b: Number(e.target.value) })}
                  className="input py-1.5"
                >
                  <option value={7.0}>7 Billion Parameters (Llama-3-8B / Mistral-7B)</option>
                  <option value={13.0}>13 Billion Parameters (Standard Mid-tier)</option>
                  <option value={70.0}>70 Billion Parameters (Llama-3-70B / Enterprise)</option>
                  <option value={405.0}>405 Billion Parameters (Frontier Scale)</option>
                </select>
              </div>

              <div>
                <label className="label block mb-1">Target Accelerator Hardware</label>
                <select
                  value={tokenForm.hardware}
                  onChange={(e) => setTokenForm({ ...tokenForm, hardware: e.target.value })}
                  className="input py-1.5"
                >
                  <option value="h100">NVIDIA H100 SXM5 (700W TDP &middot; FP8 Engine)</option>
                  <option value="a100">NVIDIA A100 80GB (400W TDP &middot; Standard Cloud)</option>
                  <option value="rtx_4090">NVIDIA RTX 4090 (450W TDP &middot; Edge Workstation)</option>
                  <option value="cpu">x86_64 Datacenter CPU (Xeon / EPYC)</option>
                  <option value="npu">Dedicated NPU / Apple Neural Engine</option>
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="label block mb-1">Tokens / Request</label>
                  <input
                    type="number"
                    value={tokenForm.token_count}
                    onChange={(e) => setTokenForm({ ...tokenForm, token_count: Number(e.target.value) })}
                    className="input py-1.5 font-mono"
                  />
                </div>
                <div>
                  <label className="label block mb-1">Grid Intensity (g/kWh)</label>
                  <input
                    type="number"
                    value={tokenForm.grid_intensity}
                    onChange={(e) => setTokenForm({ ...tokenForm, grid_intensity: Number(e.target.value) })}
                    className="input py-1.5 font-mono"
                  />
                </div>
              </div>
            </div>

            <button
              onClick={handleRunTokenCalc}
              disabled={tokenLoading}
              className="btn-primary w-full py-2.5 text-xs font-semibold flex items-center justify-center gap-2"
            >
              {tokenLoading ? <RefreshCw size={14} className="animate-spin" /> : <Zap size={14} />}
              Model Token Energy &amp; Carbon Impact
            </button>
          </div>

          <div className="lg:col-span-7 space-y-4">
            {tokenResult ? (
              <div className="space-y-4">
                <div className="grid sm:grid-cols-2 gap-3">
                  <div className="card p-4">
                    <p className="label">Inference Energy</p>
                    <p className="text-xl font-bold font-mono text-slate-900 mt-1">
                      {tokenResult.joules_per_run.toFixed(3)} <span className="text-xs text-slate-500 font-normal">Joules</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">
                      {(tokenResult.joules_per_run / 3600).toFixed(6)} Wh per {tokenForm.token_count} tokens
                    </p>
                  </div>

                  <div className="card p-4">
                    <p className="label">Inference Carbon</p>
                    <p className="text-xl font-bold font-mono text-emerald-700 mt-1">
                      {tokenResult.gco2e_per_run.toFixed(6)} <span className="text-xs text-slate-500 font-normal">gCO₂e</span>
                    </p>
                    <p className="text-[11px] text-slate-500 mt-1">Direct operational footprint</p>
                  </div>
                </div>

                <div className="card p-5 space-y-3">
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
                </div>
              </div>
            ) : (
              <div className="card p-12 text-center text-slate-500 space-y-3">
                <Zap size={36} className="mx-auto text-slate-300" />
                <p className="text-sm font-semibold text-slate-700">Token Model Uncomputed</p>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Simulate energy consumption across NVIDIA H100 and A100 architectures under varying sequence lengths.
                </p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

