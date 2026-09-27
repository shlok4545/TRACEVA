import { Wifi, WifiOff } from 'lucide-react';

export type ConnectivityState = 'ONLINE' | 'OFFLINE' | 'SYNCING' | 'SYNC_ERROR';

type ConnectivityIndicatorProps = {
  state: ConnectivityState;
  pendingActions?: number;
};

const labels: Record<ConnectivityState, string> = {
  ONLINE: 'Online',
  OFFLINE: 'Offline',
  SYNCING: 'Syncing',
  SYNC_ERROR: 'Sync error',
};

export function ConnectivityIndicator({ state, pendingActions = 0 }: ConnectivityIndicatorProps) {
  const isOnline = state === 'ONLINE';
  const isSyncing = state === 'SYNCING';
  const Icon = isOnline ? Wifi : WifiOff;

  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-sm text-slate-700 shadow-sm">
      <Icon size={14} className={isOnline ? 'text-emerald-600' : isSyncing ? 'text-amber-600' : 'text-slate-500'} />
      <span className="font-medium">{labels[state]}</span>
      {pendingActions > 0 && state !== 'ONLINE' && (
        <span className="text-xs text-slate-500">• {pendingActions} pending sync</span>
      )}
    </div>
  );
}
