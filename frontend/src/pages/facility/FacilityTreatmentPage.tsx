import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Stethoscope, Eye, Clock, CheckCircle2, AlertCircle } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api, type TreatmentRecord } from '../../services/api';

function toneForStatus(status: string) {
  const value = String(status || '').toUpperCase();
  if (value === 'VERIFIED') return 'success';
  if (value === 'PENDING') return 'warning';
  if (value === 'REQUIRES_REVIEW') return 'info';
  return 'neutral';
}

function toneForIntake(status: string) {
  const value = String(status || '').toUpperCase();
  if (value === 'RECEIVED') return 'success';
  if (value === 'PENDING') return 'warning';
  return 'neutral';
}

export function FacilityTreatmentPage() {
  const { token } = useAuth();
  const [records, setRecords] = useState<TreatmentRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getTreatmentRecords(token)
      .then((data) => {
        if (active) setRecords(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load treatment records.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Treatment facility</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Treatment Verification</h1>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <Stethoscope size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Treatment records</h2>
              <p className="text-sm text-slate-500">Processing and disposal verification</p>
            </div>
          </div>
          <Badge variant="info">{records.length} records</Badge>
        </div>

        {loading && <div className="text-sm text-slate-500">Loading treatment records...</div>}
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <Table
            headers={['Record ID', 'Passport', 'Received', 'Weight', 'Seal', 'Intake', 'Method', 'Verification', 'Status', 'Actions']}
            rows={records.map((record) => [
              <span className="font-mono text-slate-900">#{record.id}</span>,
              <Link to={`/facility/treatment/${record.id}`} className="font-mono text-slate-900 hover:underline">{record.passport_id}</Link>,
              record.received_at ? new Date(record.received_at).toLocaleString() : '—',
              `${record.received_weight_kg.toFixed(1)} kg`,
              <StatusBadge tone={toneForStatus(record.seal_condition)}>{record.seal_condition}</StatusBadge>,
              <StatusBadge tone={toneForIntake(record.intake_status)}>{record.intake_status}</StatusBadge>,
              record.treatment_method || '—',
              <StatusBadge tone={toneForStatus(record.verification_status)}>{record.verification_status}</StatusBadge>,
              record.treatment_completed_at
                ? <span className="text-emerald-600 font-medium">Completed</span>
                : record.treatment_started_at
                  ? <span className="text-amber-600 font-medium">In Progress</span>
                  : <span className="text-slate-500">Not Started</span>,
              <div className="flex items-center gap-2">
                <Link to={`/facility/treatment/${record.id}`}>
                  <Button variant="ghost" size="sm" aria-label="View treatment detail">
                    <Eye size={14} />
                  </Button>
                </Link>
              </div>,
            ])}
          />
        )}

        {!loading && !error && records.length === 0 && (
          <div className="text-center text-slate-500 py-8">
            <Stethoscope size={32} className="mx-auto mb-2 opacity-40" />
            <p>No treatment records yet.</p>
            <p className="text-sm">Accept inbound waste at <Link to="/facility/receiving" className="underline">Receiving</Link> to create treatment records.</p>
          </div>
        )}
      </Card>
    </div>
  );
}