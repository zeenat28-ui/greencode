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

ChartJS.register(CategoryScale, LinearScale, BarElement, Tooltip, Legend, Title);

interface ViolationChartProps {
  breakdown: Record<string, number>;
}

export default function ViolationChart({ breakdown }: ViolationChartProps) {
  const labels = Object.keys(breakdown).map((k) => k.replace(/_/g, ' '));
  const data = Object.values(breakdown);

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Violation Count',
        data,
        backgroundColor: '#dc2626',
        borderColor: '#dc2626',
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: 'Violations by Type',
        color: '#334155',
        font: { size: 14, weight: 700 },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#64748b' } },
      y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } },
    },
  };

  if (Object.keys(breakdown).length === 0) {
    return (
      <div className="text-center py-8 text-slate-400">
        No violations detected
      </div>
    );
  }

  return <Bar data={chartData} options={options} />;
}

interface LanguageChartProps {
  breakdown: Record<string, number>;
}

export function LanguageChart({ breakdown }: LanguageChartProps) {
  const entries = Object.entries(breakdown);
  const labels = entries.map(([k]) => k);
  const data = entries.map(([_, v]) => v);

  const chartData = {
    labels,
    datasets: [
      {
        label: 'Files',
        data,
        backgroundColor: '#10b981',
        borderColor: '#059669',
        borderRadius: 4,
      },
    ],
  };

  const options = {
    responsive: true,
    plugins: {
      legend: { display: false },
      title: {
        display: true,
        text: 'Languages Detected',
        color: '#334155',
        font: { size: 14, weight: 700 },
      },
    },
    scales: {
      x: { grid: { display: false }, ticks: { color: '#64748b' } },
      y: { grid: { color: '#f1f5f9' }, ticks: { color: '#64748b' } },
    },
  };

  return <Bar data={chartData} options={options} />;
}

interface ScoreGaugeProps {
  score: number;
  threshold: number;
}

export function ScoreGauge({ score, threshold }: ScoreGaugeProps) {
  const pct = Math.max(0, Math.min(100, score));
  const isPass = score >= threshold;
  const barColor = isPass ? '#22c55e' : '#dc2626';

  return (
    <div className="text-center">
      <div className="relative w-32 h-32 mx-auto mb-2">
        <svg className="w-full h-full" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#f1f5f9"
            strokeWidth="8"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={barColor}
            strokeWidth="8"
            strokeDasharray={`${2 * Math.PI * 40}`}
            strokeDashoffset={2 * Math.PI * 40 * (1 - pct / 100)}
            transform="rotate(-90 50 50)"
            style={{ transition: 'all 0.5s ease' }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className="text-2xl font-black" style={{ color: barColor }}>
            {pct.toFixed(0)}
          </span>
          <span className="text-xs text-slate-500">% Green</span>
        </div>
      </div>
      <p className="text-sm text-slate-600">
        Threshold: <span className="font-bold">{threshold}</span>
      </p>
      <p className="text-sm font-bold" style={{ color: barColor }}>
        {isPass ? 'PASSED' : 'BLOCKED'}
      </p>
    </div>
  );
}
