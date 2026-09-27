import type { ReactNode } from 'react';

type MetricCardProps = {
  label: string;
  value: string;
  change?: string;
  tone?: 'default' | 'success' | 'warning' | 'danger';
  icon?: ReactNode;
};

const tones = {
  default: 'bg-slate-50 text-slate-900',
  success: 'bg-emerald-50 text-emerald-900',
  warning: 'bg-amber-50 text-amber-900',
  danger: 'bg-rose-50 text-rose-900',
};

export function MetricCard({ label, value, change, tone = 'default', icon }: MetricCardProps) {
  return (
    <div className={`rounded-xl border border-slate-200 p-4 ${tones[tone]}`}>
      <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
        <span>{label}</span>
        {icon}
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      {change && <div className="mt-2 text-xs text-slate-500">{change}</div>}
    </div>
  );
}
