import { useState } from 'react';
import { 
  DollarSign, Calculator, Server, Leaf, Zap, ArrowRight, 
  CheckCircle2, X, Sliders, TrendingDown, Cpu, Sparkles 
} from 'lucide-react';

interface FinOpsCalculatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  violationsCount?: number;
}

interface InstanceTypeOption {
  id: string;
  name: string;
  provider: string;
  specs: string;
  hourlyRate: number; // USD per hour
  watts: number;
}

const INSTANCE_OPTIONS: InstanceTypeOption[] = [
  {
    id: 'c6i.2xlarge',
    name: 'AWS c6i.2xlarge',
    provider: 'Amazon Web Services',
    specs: '8 vCPU, 16 GiB RAM (Compute Optimized)',
    hourlyRate: 0.34,
    watts: 180,
  },
  {
    id: 'g5.xlarge',
    name: 'AWS g5.xlarge (GPU)',
    provider: 'Amazon Web Services',
    specs: '4 vCPU, 16 GiB RAM, NVIDIA A10G (AI / LLM)',
    hourlyRate: 1.006,
    watts: 320,
  },
  {
    id: 'm6g.2xlarge',
    name: 'AWS m6g.2xlarge (Graviton)',
    provider: 'Amazon Web Services',
    specs: '8 vCPU ARM Graviton2, 32 GiB RAM',
    hourlyRate: 0.308,
    watts: 120,
  },
  {
    id: 'n2-standard-8',
    name: 'GCP n2-standard-8',
    provider: 'Google Cloud Platform',
    specs: '8 vCPU, 32 GiB RAM (General Purpose)',
    hourlyRate: 0.388,
    watts: 190,
  },
];

export default function FinOpsCalculatorModal({
  isOpen,
  onClose,
  violationsCount = 4,
}: FinOpsCalculatorModalProps) {
  const [selectedInstance, setSelectedInstance] = useState<InstanceTypeOption>(INSTANCE_OPTIONS[0]);
  const [nodeCount, setNodeCount] = useState<number>(20); // 20 production instances
  const [efficiencyGainPct, setEfficiencyGainPct] = useState<number>(38); // 38% CPU optimization
  const [gridIntensity, setGridIntensity] = useState<number>(215); // gCO2e/kWh

  if (!isOpen) return null;

  // Monthly hours: 730 hours / month
  const hoursPerMonth = 730;
  const baselineMonthlySpend = nodeCount * selectedInstance.hourlyRate * hoursPerMonth;
  // Compute savings proportional to algorithmic speedup & instance rightsizing potential
  const savingsPct = efficiencyGainPct / 100;
  const monthlySavings = baselineMonthlySpend * (savingsPct * 0.75); // conservative 75% realization
  const annualSavings = monthlySavings * 12;
  const optimizedMonthlySpend = baselineMonthlySpend - monthlySavings;

  // Carbon metrics
  const monthlyKwhBaseline = (nodeCount * selectedInstance.watts * hoursPerMonth) / 1000;
  const monthlyKwhSaved = monthlyKwhBaseline * savingsPct;
  const annualKwhSaved = monthlyKwhSaved * 12;
  const annualCo2TonnesSaved = (annualKwhSaved * gridIntensity) / 1000 / 1000;

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-slate-900/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div 
        className="bg-white rounded-xl shadow-2xl border border-slate-200 w-full max-w-3xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="bg-slate-900 text-white px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-600 flex items-center justify-center text-white shadow-sm">
              <DollarSign size={18} />
            </div>
            <div>
              <h3 className="text-sm font-bold tracking-tight text-white flex items-center gap-2">
                FinOps &amp; GreenOps Cloud Cost Estimator
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 font-mono">
                  Real-World ROI
                </span>
              </h3>
              <p className="text-[11px] text-slate-400">
                Model compute infrastructure savings and Scope 2 carbon reductions from algorithmic optimization
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800"
          >
            <X size={16} />
          </button>
        </div>

        <div className="p-6 space-y-6 text-slate-800 max-h-[82vh] overflow-y-auto">
          {/* Controls Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Instance Selection */}
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-500 block mb-1.5">
                Target Cloud Instance Tier
              </label>
              <div className="space-y-2">
                {INSTANCE_OPTIONS.map((inst) => (
                  <button
                    key={inst.id}
                    onClick={() => setSelectedInstance(inst)}
                    className={`w-full text-left p-2.5 rounded-lg border text-xs transition-all flex items-center justify-between ${
                      selectedInstance.id === inst.id
                        ? 'border-emerald-600 bg-emerald-50/60 ring-1 ring-emerald-600'
                        : 'border-slate-200 hover:border-slate-300 bg-slate-50/40'
                    }`}
                  >
                    <div>
                      <div className="font-bold text-slate-900 font-mono">{inst.name}</div>
                      <div className="text-[11px] text-slate-500">{inst.specs}</div>
                    </div>
                    <div className="text-right font-mono">
                      <div className="font-bold text-emerald-700">${inst.hourlyRate}/hr</div>
                      <div className="text-[10px] text-slate-400">{inst.watts}W draw</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Workload Sliders */}
            <div className="p-4 rounded-xl border border-slate-200 bg-slate-50/70 space-y-4">
              <div>
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-1">
                  <span>Production Nodes / Pods</span>
                  <span className="font-mono text-emerald-700 font-extrabold">{nodeCount} instances</span>
                </div>
                <input
                  type="range"
                  min="2"
                  max="100"
                  step="2"
                  value={nodeCount}
                  onChange={(e) => setNodeCount(Number(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                  <span>2 nodes (Startup)</span>
                  <span>20 nodes</span>
                  <span>100 nodes (Enterprise)</span>
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between text-xs font-bold text-slate-700 mb-1">
                  <span>Algorithmic Optimization Rate</span>
                  <span className="font-mono text-emerald-700 font-extrabold">{efficiencyGainPct}% CPU cut</span>
                </div>
                <input
                  type="range"
                  min="15"
                  max="70"
                  step="1"
                  value={efficiencyGainPct}
                  onChange={(e) => setEfficiencyGainPct(Number(e.target.value))}
                  className="w-full accent-emerald-600 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-slate-400 font-mono mt-0.5">
                  <span>15% (Hoisting)</span>
                  <span>38% (O(N) Lookups)</span>
                  <span>70% (Vectorized/INT8)</span>
                </div>
              </div>

              <div className="p-2.5 rounded-lg bg-white border border-slate-200 text-xs flex items-center justify-between">
                <span className="text-slate-500">Electricity Grid Intensity:</span>
                <span className="font-mono font-bold text-slate-800">{gridIntensity} gCO₂e/kWh</span>
              </div>
            </div>
          </div>

          {/* ROI Metric Cards Banner */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="p-4 rounded-xl bg-gradient-to-br from-emerald-50 to-emerald-100/40 border border-emerald-200">
              <div className="text-[11px] font-bold uppercase tracking-wider text-emerald-900 flex items-center gap-1.5 mb-1">
                <TrendingDown size={14} className="text-emerald-700" />
                Annual Cloud Bill Savings
              </div>
              <div className="text-2xl font-black text-emerald-950 font-mono">
                ${Math.round(annualSavings).toLocaleString()}
              </div>
              <div className="text-[11px] text-emerald-800 mt-1 font-medium">
                ~${Math.round(monthlySavings).toLocaleString()} / month direct compute reduction
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5 mb-1">
                <Leaf size={14} className="text-olive-700" />
                Scope 2 Carbon Avoided
              </div>
              <div className="text-2xl font-black text-slate-900 font-mono">
                {annualCo2TonnesSaved.toFixed(2)} <span className="text-sm font-normal text-slate-500">tonnes</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                Equivalent to ~{Math.round(annualCo2TonnesSaved * 2480)} miles driven avoided
              </div>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-200">
              <div className="text-[11px] font-bold uppercase tracking-wider text-slate-600 flex items-center gap-1.5 mb-1">
                <Zap size={14} className="text-olive-700" />
                Electricity Reduction
              </div>
              <div className="text-2xl font-black text-slate-900 font-mono">
                {Math.round(annualKwhSaved).toLocaleString()} <span className="text-sm font-normal text-slate-500">kWh</span>
              </div>
              <div className="text-[11px] text-slate-500 mt-1">
                From eliminated redundant CPU loops &amp; VRAM
              </div>
            </div>
          </div>

          {/* Spend Comparison Bar */}
          <div className="p-4 rounded-xl border border-slate-200 bg-white space-y-2">
            <div className="flex items-center justify-between text-xs font-bold text-slate-700">
              <span>Monthly Cloud Spend (Before vs After GreenCode)</span>
              <span className="font-mono text-emerald-700">
                {(savingsPct * 75).toFixed(0)}% Budget Recaptured
              </span>
            </div>
            
            <div className="space-y-1.5 font-mono text-xs">
              <div className="flex items-center justify-between text-slate-500">
                <span>Baseline Compute ({nodeCount} nodes):</span>
                <span className="font-bold text-slate-900">${Math.round(baselineMonthlySpend).toLocaleString()} / mo</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                <div className="bg-rose-500 h-full rounded-full w-full" />
              </div>

              <div className="flex items-center justify-between text-slate-500 pt-1">
                <span>With GreenCode Eco-Refactoring:</span>
                <span className="font-bold text-emerald-800">${Math.round(optimizedMonthlySpend).toLocaleString()} / mo</span>
              </div>
              <div className="w-full bg-slate-200 rounded-full h-3 overflow-hidden">
                <div 
                  className="bg-emerald-600 h-full rounded-full transition-all duration-500" 
                  style={{ width: `${(optimizedMonthlySpend / baselineMonthlySpend) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Executive Value Proposition */}
          <div className="p-3.5 rounded-lg bg-olive-50/70 border border-olive-200 text-xs text-olive-950 flex items-start gap-2.5">
            <Sparkles size={16} className="text-olive-700 shrink-0 mt-0.5" />
            <div className="leading-relaxed">
              <strong>Enterprise Decision Maker Takeaway:</strong> GreenCode allows engineering teams to meet ESG board requirements and sustainability goals while simultaneously slashing AWS/Azure bills with <strong>zero architecture redesign</strong>.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

