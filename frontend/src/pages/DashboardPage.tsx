import { useEffect, useMemo, useState } from 'react';
import { AlertTriangle, ArrowUpRight, CheckCircle2, ClipboardCheck, Trash2, Truck } from 'lucide-react';

import { Badge } from '../components/ui/Badge';
import { Card } from '../components/ui/Card';
import { MetricCard } from '../components/ui/MetricCard';
import { StatusBadge } from '../components/ui/StatusBadge';
import { Table } from '../components/ui/Table';
import { useAuth } from '../contexts/AuthContext';
import { api, type DashboardSummaryResponse } from '../services/api';

type DashboardPageProps = {
  backendStatus: 'Connected' | 'Disconnected';
};

function toneForStatus(status: string) {
  const value = String(status || '').toUpperCase();
  if (value.includes('CRITICAL') || value.includes('DANGER') || value.includes('ESCALATED')) return 'danger';
  if (value.includes('WARNING') || value.includes('PENDING') || value.includes('DUE')) return 'warning';
  if (value.includes('SUCCESS') || value.includes('VERIFIED') || value.includes('COMPLETED')) return 'success';
  return 'neutral';
}

export function DashboardPage({ backendStatus }: DashboardPageProps) {
  const { token } = useAuth();
  const [summary, setSummary] = useState<DashboardSummaryResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getDashboardSummary(token)
      .then((data) => {
        if (active) {
          setSummary(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load dashboard data.');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  const metrics = useMemo(() => {
    if (!summary) {
      return [
        { label: 'Active Passports', value: '--', change: 'Loading', tone: 'default' as const, icon: <ClipboardCheck size={16} /> },
        { label: 'Risk Alerts', value: '--', change: 'Loading', tone: 'warning' as const, icon: <AlertTriangle size={16} /> },
        { label: 'Pickup SLA', value: '--', change: 'Loading', tone: 'success' as const, icon: <Truck size={16} /> },
        { label: 'Treatment Verified', value: '--', change: 'Loading', tone: 'danger' as const, icon: <CheckCircle2 size={16} /> },
      ];
    }

    const ps = summary.passport_summary ?? { total: 0, active: 0, completed: 0, total_weight_kg: 0 };
    const rs = summary.risk_summary ?? { low: 0, medium: 0, high: 0, critical: 0, distribution: {} };
    const pks = summary.pickup_summary ?? { total_requests: 0, completed: 0, pending: 0, overdue: 0, average_waiting_time_minutes: 0, average_response_time_minutes: 0, priority_distribution: {} };
    const ts = summary.treatment_summary ?? { received_count: 0, treatment_pending: 0, treatment_completed: 0, verification_pending: 0, verified: 0, rejected: 0, average_treatment_completion_hours: 0 };

    return [
      { label: 'Active Passports', value: String(ps.active), change: `${ps.total} total`, tone: 'default' as const, icon: <ClipboardCheck size={16} /> },
      { label: 'Risk Alerts', value: String(rs.critical + rs.high), change: `${rs.critical} critical`, tone: 'warning' as const, icon: <AlertTriangle size={16} /> },
      { label: 'Pickup SLA', value: `${Math.max(0, 100 - Math.round((pks.overdue / Math.max(1, pks.total_requests)) * 100))}%`, change: `${pks.pending} pending`, tone: 'success' as const, icon: <Truck size={16} /> },
      { label: 'Treatment Verified', value: `${ts.verified || 0}`, change: `${ts.verification_pending || 0} pending`, tone: 'danger' as const, icon: <CheckCircle2 size={16} /> },
    ];
  }, [summary]);

  return (
    <div className="space-y-6 min-h-0 w-full">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Operations Overview</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">Hospital Safety Dashboard</h1>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="neutral">Live system</Badge>
          <StatusBadge tone={backendStatus === 'Connected' ? 'success' : 'warning'}>{backendStatus === 'Connected' ? 'Backend: Connected' : 'Backend: Offline'}</StatusBadge>
        </div>
      </div>

      {loading && (
        <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500" role="status">
          Loading live operational data...
        </div>
      )}
      {error && (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700" role="alert">
          {error}
        </div>
      )}

      <section aria-label="Key metrics" className="grid gap-4 grid-cols-1 md:grid-cols-2 xl:grid-cols-4 min-h-[120px]">
        {metrics.map((metric) => (
          <MetricCard key={metric.label} {...metric} />
        ))}
      </section>

      <div className="grid gap-6 xl:grid-cols-[1.4fr_0.8fr]">
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Operational pulse</h2>
              <p className="text-sm text-slate-500">Waste collection and compliance status</p>
            </div>
            <Badge variant="info">Updated live</Badge>
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Critical bags</span>
                <Trash2 size={16} className="text-rose-500" />
              </div>
              <div className="text-2xl font-semibold text-slate-900">{summary?.risk_summary?.critical ?? 0}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Pending pickups</span>
                <Truck size={16} className="text-amber-500" />
              </div>
              <div className="text-2xl font-semibold text-slate-900">{summary?.pickup_summary?.pending ?? 0}</div>
            </div>
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-2 flex items-center justify-between text-sm text-slate-500">
                <span>Compliance score</span>
                <ArrowUpRight size={16} className="text-emerald-500" />
              </div>
              <div className="text-2xl font-semibold text-slate-900">{summary ? `${Math.min(99, Math.max(0, 100 - ((summary.incident_summary?.open ?? 0) * 5)))}%` : '--'}</div>
            </div>
          </div>
        </Card>

        <Card>
          <h2 className="text-lg font-semibold text-slate-900">Priority alerts</h2>
          <div className="mt-4 space-y-3">
            {((summary?.alerts ?? []) as Array<{ key: string; severity: string; title: string; message: string; entity: string; entity_id: number | null }>).slice(0, 3).map((alert) => (
              <div key={alert.key} className={`rounded-lg border p-3 text-sm ${alert.severity === 'CRITICAL' || alert.severity === 'HIGH' ? 'border-rose-200 bg-rose-50 text-rose-700' : alert.severity === 'MEDIUM' ? 'border-amber-200 bg-amber-50 text-amber-700' : 'border-sky-200 bg-sky-50 text-sky-700'}`}>
                {alert.title}
              </div>
            ))}
            {(!summary || (summary?.alerts?.length ?? 0) === 0) && <div className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm text-slate-600">No active alerts.</div>}
          </div>
        </Card>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-slate-900">Recent activity</h2>
            <p className="text-sm text-slate-500">Most recent waste lifecycle events</p>
          </div>
        </div>

        <Table
          headers={['Event', 'Entity', 'Status', 'Message', 'Updated']}
          rows={
            ((summary?.recent_activity ?? []) as Array<{ event_type: string; timestamp: string; entity: string; actor: string; message: string; severity: string }>).slice(0, 6).map((item) => [
              item.event_type ?? '—',
              item.entity ?? '—',
              <StatusBadge key={`${item.entity}-${item.timestamp}`} tone={toneForStatus(item.severity ?? 'LOW')}> {String(item.severity ?? 'LOW').toUpperCase()} </StatusBadge>,
              item.message ?? '—',
              item.timestamp ? new Date(item.timestamp).toLocaleString() : '—',
            ])
          }
        />
      </Card>
    </div>
  );
}
