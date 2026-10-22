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
import { BarChart3, ListFilter, CheckCircle2 } from 'lucide-react';
import { useT } from '../../i18n/I18nContext';

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend, Title);

interface ViolationChartProps {
  breakdown: Record<string, number>;
}

const FRIENDLY_NAMES: Record<string, { label: string; desc: string; color: string }> = {
  QUADRATIC_STRING_CONCAT_IN_LOOP: { label: 'Quadratic String Allocation', desc: 'O(N²) buffer reallocation inside loop', color: 'bg-rose-500' },
  'NESTED_LOOPS_DEPTH_3+': { label: 'Deep Nested Iteration (O(N³))', desc: 'Polynomial time complexity amplification', color: 'bg-amber-500' },
  RAW_DB_CURSOR_NO_CONTEXT: { label: 'Unscoped Database Cursor', desc: 'Connection lifecycle leak without context manager', color: 'bg-amber-500' },
  UNCACHED_NETWORK_IN_LOOP: { label: 'Unbatched Network I/O in Loop', desc: 'Repeated synchronous round-trips inside loop', color: 'bg-rose-500' },
  INEFFICIENT_LOOP: { label: 'Inefficient Loop', desc: 'Excessive CPU cycles per iteration', color: 'bg-amber-500' },
  NESTED_LOOPS: { label: 'Deeply Nested Loops', desc: 'O(N²) or O(N³) algorithmic complexity', color: 'bg-rose-500' },
  REDUNDANT_COMPUTATION: { label: 'Redundant Computation', desc: 'Recalculating invariant expressions repeatedly', color: 'bg-amber-500' },
  BLOCKING_IO: { label: 'Blocking I/O in Loop', desc: 'Synchronous I/O wait holding worker thread', color: 'bg-rose-500' },
  UNINDEXED_QUERY: { label: 'Unindexed Query', desc: 'Full table scan increasing database CPU draw', color: 'bg-amber-500' },
};

function formatLabel(key: string): { label: string; desc: string; color: string } {
  if (FRIENDLY_NAMES[key]) return FRIENDLY_NAMES[key];
  const cleaned = key.replace(/_/g, ' ').toLowerCase();
  const title = cleaned.charAt(0).toUpperCase() + cleaned.slice(1);
  return { label: title, desc: 'Static efficiency pattern', color: 'bg-emerald-600' };
}

export default function ViolationChart({ breakdown }: ViolationChartProps) {
  const t = useT();
  const [viewMode, setViewMode] = useState<'bars' | 'chart'>('bars');

  const entries = Object.entries(breakdown || {}).sort((a, b) => b[1] - a[1]);
  const totalCount = entries.reduce((acc, [, val]) => acc + val, 0);

  if (entries.length === 0 || totalCount === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-8 text-center">
        <div className="w-9 h-9 rounded-full bg-emerald-50 border border-emerald-200 flex items-center justify-center text-emerald-600 mb-2">
          <CheckCircle2 size={18} />
        </div>
        <p className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">{t('charts.empty.title')}</p>
        <p className="text-[11px] text-zinc-500 dark:text-zinc-400 mt-0.5">{t('charts.empty.body')}</p>
      </div>
    );
  }

  const maxCount = entries[0]?.[1] || 1;

  const chartData = {
    labels: entries.map(([k]) => formatLabel(k).label),
    datasets: [
      {
        label: t('charts.findings'),
        data: entries.map(([, v]) => v),
        backgroundColor: 'var(--gc-color-accent-emerald)',
        hoverBackgroundColor: 'var(--gc-color-emerald-hover)',
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
        backgroundColor: 'var(--gc-color-surface-elevated)',
        titleFont: { size: 12, weight: 600 as const },
        bodyFont: { size: 11 },
        padding: 10,
        cornerRadius: 8,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: 'var(--gc-color-text-tertiary)', font: { size: 11 } },
      },
      y: {
        grid: { color: 'var(--gc-color-border)' },
        ticks: { color: 'var(--gc-color-text-tertiary)', font: { size: 11 }, stepSize: 1 },
      },
    },
  };

  return (
    <div className="space-y-3.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-zinc-500 dark:text-zinc-400">{t('charts.ruleBreakdown')}</span>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 font-medium">
            {t('charts.findingsCount', { count: totalCount })}
          </span>
        </div>

        <div className="flex items-center p-0.5 rounded-lg bg-zinc-100 dark:bg-zinc-800 border border-zinc-200/80 dark:border-zinc-700/80 text-xs">
          <button
            type="button"
            onClick={() => setViewMode('bars')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
              viewMode === 'bars'
                ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800'
            }`}
          >
            <ListFilter size={11} />
            {t('charts.viewModes.list')}
          </button>
          <button
            type="button"
            onClick={() => setViewMode('chart')}
            className={`flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all ${
              viewMode === 'chart'
                ? 'bg-white dark:bg-zinc-900 text-zinc-900 dark:text-zinc-100 shadow-sm'
                : 'text-zinc-500 dark:text-zinc-400 hover:text-zinc-800'
            }`}
          >
            <BarChart3 size={11} />
            {t('charts.viewModes.chart')}
          </button>
        </div>
      </div>

      {viewMode === 'bars' ? (
        <div className="space-y-2.5">
          {entries.map(([key, count]) => {
            const meta = formatLabel(key);
            const percent = Math.round((count / totalCount) * 100);
            const barWidth = Math.max(8, Math.round((count / maxCount) * 100));

            return (
              <div key={key} className="p-3 rounded-lg bg-zinc-50/70 dark:bg-zinc-800/50 border border-zinc-200/70 dark:border-zinc-700/70 hover:border-zinc-300 dark:hover:border-zinc-600 transition-all space-y-1.5">
                <div className="flex items-center justify-between text-xs gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <span className={`w-2 h-2 rounded-full shrink-0 ${meta.color}`} />
                    <span className="font-semibold text-zinc-900 dark:text-zinc-100 truncate">{meta.label}</span>
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <span className="font-mono text-[11px] text-zinc-400 dark:text-zinc-500">{percent}%</span>
                    <span className="font-mono font-semibold text-[11px] bg-white dark:bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-200 dark:border-zinc-700 text-zinc-800 dark:text-zinc-200">
                      {count}
                    </span>
                  </div>
                </div>

                <div className="w-full bg-zinc-200/70 dark:bg-zinc-700/50 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500 bg-zinc-900 dark:bg-zinc-600"
                    style={{ width: `${barWidth}%` }}
                  />
                </div>

                <p className="text-[11px] text-zinc-500 dark:text-zinc-400 leading-tight">
                  {meta.desc}
                </p>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="h-52 w-full pt-2">
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
  const t = useT();
  const entries = Object.entries(breakdown || {}).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, val]) => acc + val, 0);

  if (entries.length === 0 || total === 0) {
    return <div className="text-center py-8 text-xs text-zinc-400 dark:text-zinc-500">{t('charts.empty.noLanguageData')}</div>;
  }

  return (
    <div className="space-y-3 pt-1">
      {entries.map(([lang, count]) => {
        const pct = Math.round((count / total) * 100);
        return (
          <div key={lang} className="space-y-1">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-zinc-800 dark:text-zinc-200 capitalize">{lang}</span>
              <span className="font-mono text-zinc-500 dark:text-zinc-400">{count} files ({pct}%)</span>
            </div>
            <div className="w-full bg-zinc-100 dark:bg-zinc-700/50 rounded-full h-1.5 overflow-hidden">
              <div
                className="h-full rounded-full transition-all duration-500 bg-emerald-600"
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
  const t = useT();
  const pct = Math.max(0, Math.min(100, Math.round(score)));
  const isPass = pct >= threshold;
  const strokeColor = isPass ? 'var(--gc-color-emerald)' : 'var(--gc-color-rose)';

  return (
    <div className="text-center">
      <div className="relative w-32 h-32 mx-auto mb-2">
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="var(--gc-color-border)"
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
          <span className="text-3xl font-bold font-mono" style={{ color: strokeColor }}>
            {pct}
          </span>
          <span className="text-[10px] uppercase font-semibold text-zinc-400 dark:text-zinc-500 tracking-wider">{t('charts.score')}</span>
        </div>
      </div>
      <p className="text-xs text-zinc-500 dark:text-zinc-400 font-medium">
        {t('charts.target', { threshold: String(threshold) })}
      </p>
      <div className="mt-1">
        <span className={`inline-block px-2.5 py-0.5 rounded-md text-[10px] font-semibold uppercase tracking-wider ${
          isPass ? 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-900 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-700' : 'bg-rose-50 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 border border-rose-200 dark:border-rose-700'
        }`}>
          {isPass ? t('charts.gate.passed') : t('charts.gate.required')}
        </span>
      </div>
    </div>
  );
}
