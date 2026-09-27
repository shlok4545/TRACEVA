import { CloudUpload, ListTodo } from 'lucide-react';

type OfflineAction = {
  id: string;
  actionType: string;
  entityRef: string;
  timestamp: string;
  status: 'PENDING' | 'SYNCING' | 'SYNCED' | 'FAILED';
  payload?: Record<string, unknown>;
};

type OfflineActionQueueProps = {
  actions: OfflineAction[];
};

export function OfflineActionQueue({ actions }: OfflineActionQueueProps) {
  if (!actions.length) {
    return (
      <div className="rounded-xl border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        No offline actions queued.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {actions.map((action) => (
        <div key={action.id} className="rounded-xl border border-slate-200 bg-white p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-sm font-medium text-slate-800">
              <ListTodo size={14} className="text-slate-500" />
              {action.actionType}
            </div>
            <span className="rounded-full bg-slate-100 px-2 py-0.5 text-[10px] uppercase tracking-wide text-slate-600">
              {action.status}
            </span>
          </div>
          <div className="mt-2 text-xs text-slate-500">{action.entityRef}</div>
          <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
            <span>{new Date(action.timestamp).toLocaleString()}</span>
            {action.status === 'PENDING' && <CloudUpload size={14} className="text-amber-600" />}
          </div>
        </div>
      ))}
    </div>
  );
}
