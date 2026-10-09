import React, { useState } from 'react';
import { ShieldCheck, ShieldAlert, Sliders, Save, CheckCircle2 } from 'lucide-react';

export default function Policies() {
  const [maxRegression, setMaxRegression] = useState(25.0);
  const [minGreenScore, setMinGreenScore] = useState(80.0);
  const [warningThreshold, setWarningThreshold] = useState(70.0);
  const [criticalThreshold, setCriticalThreshold] = useState(90.0);
  const [autoBlock, setAutoBlock] = useState(true);
  const [autoRollback, setAutoRollback] = useState(true);
  const [dirtyGridLimit, setDirtyGridLimit] = useState(450.0);
  const [savedSuccess, setSavedSuccess] = useState(false);

  const handleSave = () => {
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 3000);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
        <div>
          <h1 className="text-xl font-bold text-slate-900">Enterprise Energy Policy & Guardrail Engine</h1>
          <p className="text-sm text-slate-500">Configure binding CI/CD gates and automated Kubernetes rollback triggers</p>
        </div>
        <button 
          onClick={handleSave}
          className="bg-emerald-600 hover:bg-emerald-700 text-white font-medium px-4 py-2 rounded-lg text-sm flex items-center gap-1.5 transition-colors shadow-sm"
        >
          <Save className="w-4 h-4" /> Save Policy Rules
        </button>
      </div>

      {savedSuccess && (
        <div className="bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm p-4 rounded-xl flex items-center gap-2">
          <CheckCircle2 className="w-5 h-5 text-emerald-600" />
          <span>Policies successfully updated and synchronized across all deployment sentinels.</span>
        </div>
      )}

      {/* Rules Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <h2 className="font-semibold text-slate-900 text-base flex items-center gap-2">
            <Sliders className="w-4 h-4 text-emerald-600" /> CI/CD Pre-Deploy Gating Rules
          </h2>

          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider block mb-1">
              Max Allowable Energy Regression vs Baseline (%)
            </label>
            <input 
              type="number" 
              value={maxRegression} 
              onChange={(e) => setMaxRegression(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 mt-1 block">Deployments exceeding this threshold are blocked immediately.</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider block mb-1">
              Minimum Required Green Code Score (0 - 100)
            </label>
            <input 
              type="number" 
              value={minGreenScore} 
              onChange={(e) => setMinGreenScore(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 mt-1 block">GSF SCI standard baseline compliance score.</span>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoBlock} 
                onChange={(e) => setAutoBlock(e.target.checked)}
                className="w-4 h-4 text-emerald-600 rounded"
              />
              <span className="text-sm font-medium text-slate-900">Auto-Block Merge on Regression Violation</span>
            </label>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <h2 className="font-semibold text-slate-900 text-base flex items-center gap-2">
            <ShieldAlert className="w-4 h-4 text-blue-600" /> Production Kubernetes Sentinel Rules
          </h2>

          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider block mb-1">
              Live Pod Power Spike Rollback Limit (%)
            </label>
            <input 
              type="number" 
              value={35.0} 
              disabled
              className="w-full bg-slate-100 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-500 outline-none"
            />
            <span className="text-xs text-slate-500 mt-1 block">Fixed safety limit: Spikes &gt; 35% trigger immediate Kubernetes replica rollback.</span>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-700 uppercase tracking-wider block mb-1">
              Dirty Grid Carbon Intensity Ceiling (gCO2e / kWh)
            </label>
            <input 
              type="number" 
              value={dirtyGridLimit} 
              onChange={(e) => setDirtyGridLimit(Number(e.target.value))}
              className="w-full bg-slate-50 border border-slate-200 rounded-lg p-2.5 text-sm text-slate-900 outline-none focus:border-emerald-500"
            />
            <span className="text-xs text-slate-500 mt-1 block">High-carbon windows defer heavy non-critical batch jobs.</span>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-3 cursor-pointer">
              <input 
                type="checkbox" 
                checked={autoRollback} 
                onChange={(e) => setAutoRollback(e.target.checked)}
                className="w-4 h-4 text-blue-600 rounded"
              />
              <span className="text-sm font-medium text-slate-900">Enable Automated Kubernetes API Rollback Trigger</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  );
}

