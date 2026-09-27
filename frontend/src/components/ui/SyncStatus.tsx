import { RefreshCw } from 'lucide-react';

type SyncStatusProps = {
  state: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
  retryCount?: number;
};

const stateStyles = {
  PENDING: 'bg-slate-100 text-slate-700',
  SYNCING: 'bg-amber-100 text-amber-700',
  SYNCED: 'bg-emerald-100 text-emerald-700',
  FAILED: 'bg-rose-100 text-rose-700',
};

export function SyncStatus({ state, retryCount = 0 }: SyncStatusProps) {
  return (
    <div className="inline-flex items-center gap-2 rounded-full px-2.5 py-1 text-xs font-medium">
      <RefreshCw size={12} className={state === 'SYNCING' ? 'animate-spin' : ''} />
      <span className={stateStyles[state]}>{state}</span>
      {retryCount > 0 && <span className="text-slate-500">Retries: {retryCount}</span>}
    </div>
  );
}
