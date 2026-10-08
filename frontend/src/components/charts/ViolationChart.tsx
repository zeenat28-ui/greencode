import { useState } from 'react';
import { Bar } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  Tooltip,
  Legend,
  Title,
} from 'chart.js';
import { AlertTriangle, BarChart3, ListFilter, CheckCircle2 } from 'lucide-react';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend, Title);

interface ViolationChartProps {
  breakdown: Record<string, number>;
}

// Friendly human labels for violation codes
const FRIENDLY_NAMES: Record<string, { label: string; desc: string; color: string }> = {
  INEFFICIENT_LOOP: { label: 'Inefficient Loop', desc: 'Consumes excessive CPU cycles per iteration', color: 'bg-amber-500' },
  NESTED_LOOPS: { label: 'Deeply Nested Loops', desc: 'Exponential O(N²) or O(N³) algorithmic complexity', color: 'bg-rose-500' },
  REDUNDANT_COMPUTATION: { label: 'Redundant Computation', desc: 'Recalculating identical values repeatedly', color: 'bg-amber-600' },
  BLOCKING_IO: { label: 'Blocking I/O in Loop', desc: 'Network or disk wait holding thread idle', color: 'bg-rose-600' },
  UNINDEXED_QUERY: { label: 'Unindexed Query', desc: 'Full database table scans wasting database CPU', color: 'bg-amber-500' },
  LARGE_PAYLOAD: { label: 'Large Data Transfer', desc: 'Transferring uncompressed or unnecessary payloads', color: 'bg-blue-500' },
  UNOPTIMIZED_IMPORT: { label: 'Heavy Unused Imports', desc: 'Unnecessary memory load and parse overhead', color: 'bg-slate-500' },
  FP32_TENSOR_LOOP: { label: 'Unquantized AI Tensors', desc: 'Running FP32 inference without quantization', color: 'bg-purple-600' },
};

function formatLabel(key: string): { label: string; desc: string; color: string } {
  if (FRIENDLY_NAMES[key]) return FRIENDLY_NAMES[key];
  const cleaned = key.replace(/_/g, ' ').toLowerCase();
  const title = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return { label: title, desc: 'Algorithmic energy inefficiency', color: 'bg-olive-600' };
}

export default function ViolationChart({ breakdown }: ViolationChartProps) {
  const [viewMode, setViewMode] = useState<'bars' | 'chart'>('bars');

  const entries = Object.entries(breakdown || {}).sort((a, b) => b[1] - a[1]);
  const totalCount = entries.reduce((acc, [, val]) => acc + val, 0);

  if (entries.length === 0 || totalCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <div className="w-10 h-10 rounded-full bg-olive-50 border border-olive-200 flex items-center justify-center text-olive-700 mb-2">
          <CheckCircle2 size={20} />
        </div>
        <p className="text-xs font-bold text-slate-800">No Energy Bottlenecks Found</p>
        <p className="text-[11px] text-slate-500 mt-0.5">Your code meets Green Software Foundation efficiency guidelines.</p>
      </div>
    );
  }

  const maxCount = entries[0]?.[1] || 1;

  // ChartJS data for graph view
  const chartData = {
    labels: entries.map(([k]) => formatLabel(k).label),
    datasets: [
      {
        label: 'Issues Found',
        data: entries.map(([, v]) => v),
        backgroundColor: '#384C3B',
        hoverBackgroundColor: '#28352B',
        borderRadius: 6,
        barThickness: 16,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#0F172A',
        titleFont: { size: 12, weight: 700 as const },
        bodyFont: { size: 11 },
        padding: 10,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#64748B', font: { size: 11 } },
      },
      y: {
        grid: { color: '#F1F5F9' },
        ticks: { color: '#64748B', font: { size: 11 }, stepSize: 1 },
      },
    },
  };

  return (
    <div className="space-y-4">
      {/* View switch header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-900">Distribution</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded-full bg-slate-100 text-slate-700 font-semibold">
            {totalCount} total issues
          </span>
        </div>

        <div className="flex items-center p-0.5 rounded-lg bg-slate-100 border border-slate-200 text-xs">
          <button
            type="button"
            onClick={() => setViewMode('bars')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              viewMode === 'bars'
                ? 'bg-white text-slate-900 shadow-sm font-semibold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <ListFilter size={12} />
            Breakdown
          </button>
          <button
            type="button"
            onClick={() => setViewMode('chart')}
            className={`flex items-center gap-1 px-2.5 py-1 rounded-md text-[11px] font-medium transition-all ${
              viewMode === 'chart'
                ? 'bg-white text-slate-900 shadow-sm font-semibold'
                : 'text-slate-500 hover:text-slate-800'
            }`}
          >
            <BarChart3 size={12} />
            Chart
          </button>
        </div>
      </div>

      {viewMode === 'bars' ? (
        <div className="space-y-3 pt-1">
          {entries.map(([key, count]) => {
            const meta = formatLabel(key);
            const percent = Math.round((count / totalCount) * 100);
            const barWidth = Math.max(8, Math.round((count / maxCount) * 100));

            return (
              <div key={key} className="p-2.5 rounded-xl bg-slate-50/70 border border-slate-200/80 hover:bg-white hover:border-slate-300 transition-all space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${meta.color}`} />
                    <span className="font-bold text-slate-900">{meta.label}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-slate-500">{percent}% share</span>
                    <span className="font-mono font-bold text-xs bg-white px-2 py-0.5 rounded border border-slate-200 text-slate-800">
                      {count} {count === 1 ? 'issue' : 'issues'}
                    </span>
                  </div>
                </div>

                {/* Smooth Progress Bar */}
                <div className="w-full bg-slate-200/70 rounded-full h-2 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 bg-olive-700"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>

                <p className="text-[11px] text-slate-500 leading-tight">
                  {meta.desc}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="h-56 w-full pt-2">
          <Bar data={chartData} options={options} />
        </div>
      )}
    </div>
  );
}

interface LanguageChartProps {
  breakdown: Record<string, number>;
}

export function LanguageChart({ breakdown }: LanguageChartProps) {
  const entries = Object.entries(breakdown || {}).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, val]) => acc + val, 0);

  if (entries.length === 0 || total === 0) {
    return <div className="text-center py-8 text-xs text-slate-400">No language data recorded</div>;
  }

  return (
    <div className="space-y-3 pt-1">
      {entries.map(([lang, count]) => {
        const pct = Math.round((count / total) * 100);
        return (
          <div key={lang} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-slate-800 capitalize">{lang}</span>
              <span className="font-mono text-slate-500">{count} files ({pct}%)</span>
            </div>
            <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 bg-olive-800"
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

interface ScoreGaugeProps {
  score: number;
  threshold: number;
}

export function ScoreGauge({ score, threshold }: ScoreGaugeProps) {
  const pct = Math.max(0, Math.min(100, Math.round(score)));
  const isPass = pct >= threshold;
  const strokeColor = isPass ? '#384C3B' : '#E11D48';

  return (
    <div className="text-center">
      <div className="relative w-32 h-32 mx-auto mb-2">
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#F1F5F9"
            strokeWidth="8"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={strokeColor}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${2 * Math.PI * 40}`}
            strokeDashoffset={2 * Math.PI * 40 * (1 - pct / 100)}
            transform="rotate(-90 50 50)"
            style={{ transition: 'all 0.6s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-3xl font-black font-mono" style={{ color: strokeColor }}>
            {pct}
          </span>
          <span className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Score</span>
        </div>
      </div>
      <p className="text-xs text-slate-500 font-medium">
        Target: <span className="font-bold text-slate-700">&ge; {threshold}</span>
      </p>
      <div className="mt-1">
        <span className={`inline-block px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
          isPass ? 'bg-olive-50 text-olive-900 border border-olive-200' : 'bg-rose-50 text-rose-700 border border-rose-200'
        }`}>
          {isPass ? 'Meets Green SLA' : 'Needs Optimization'}
        </span>
      </div>
    </div>
  );
}
