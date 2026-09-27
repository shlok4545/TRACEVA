import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { MapPinned, PackageCheck, QrCode, CheckCircle2, PlayCircle } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

function toneForStatus(status: string) {
  const value = String(status || '').toUpperCase();
  if (value.includes('COLLECTED') || value.includes('COMPLETED')) return 'success';
  if (value.includes('ASSIGNED') || value.includes('IN_PROGRESS') || value.includes('ACCEPTED')) return 'warning';
  if (value.includes('QUEUED') || value.includes('REQUESTED')) return 'neutral';
  return 'info';
}

export function CollectorAssignmentsPage() {
  const { token } = useAuth();
  const [assignments, setAssignments] = useState<Array<{ id: number; passport_id: number; passport_number: string; facility_name?: string | null; ward_name?: string | null; priority: string; risk_score_snapshot?: number | null; status: string; requested_at?: string | null; created_at?: string | null; waiting_minutes?: number; due_at?: string | null; notes?: string | null }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getCollectorAssignments(token)
      .then((rows) => {
        if (active) setAssignments(rows);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load assignments.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  const handleAccept = async (pickupId: number) => {
    setProcessingId(pickupId);
    try {
      await api.acceptAssignment(token, pickupId);
      setAssignments((prev) => prev.map((a) => (a.id === pickupId ? { ...a, status: 'ACCEPTED' } : a)));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to accept assignment.');
    } finally {
      setProcessingId(null);
    }
  };

  const handleStart = async (pickupId: number) => {
    setProcessingId(pickupId);
    try {
      await api.startAssignment(token, pickupId);
      setAssignments((prev) => prev.map((a) => (a.id === pickupId ? { ...a, status: 'IN_PROGRESS' } : a)));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to start pickup.');
    } finally {
      setProcessingId(null);
    }
  };

  const canAccept = (status: string) => ['ASSIGNED', 'QUEUED'].includes(status.toUpperCase());
  const canStart = (status: string) => ['ACCEPTED', 'ASSIGNED'].includes(status.toUpperCase());

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Collector operations</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Assignments</h1>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <MapPinned size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Pickup queue</h2>
              <p className="text-sm text-slate-500">Scheduled collection tasks across active facilities</p>
            </div>
          </div>
          <Badge variant="info">{assignments.length} active</Badge>
        </div>

        {loading && <div className="text-sm text-slate-500">Loading assignments...</div>}
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <Table
            headers={['ID', 'Facility', 'Priority', 'Status', 'Waiting', 'Actions']}
            rows={assignments.map((assignment) => [
              assignment.passport_number,
              assignment.facility_name || '—',
              assignment.priority,
              <StatusBadge key={assignment.id} tone={toneForStatus(assignment.status)}>{assignment.status}</StatusBadge>,
              assignment.waiting_minutes ? `${assignment.waiting_minutes} min` : '—',
              <div className="flex items-center gap-2">
                {canAccept(assignment.status) && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => handleAccept(assignment.id)}
                    disabled={processingId === assignment.id}
                  >
                    <CheckCircle2 size={14} className="mr-1" />
                    {processingId === assignment.id ? 'Accepting...' : 'Accept'}
                  </Button>
                )}
                {canStart(assignment.status) && (
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => handleStart(assignment.id)}
                    disabled={processingId === assignment.id}
                  >
                    <PlayCircle size={14} className="mr-1" />
                    {processingId === assignment.id ? 'Starting...' : 'Start'}
                  </Button>
                )}
                <Link to={`/collector/scan?pickupId=${assignment.id}`}>
                  <Button variant="ghost" size="sm">
                    <QrCode size={14} className="mr-1" />
                    Scan
                  </Button>
                </Link>
              </div>,
            ])}
          />
        )}
      </Card>

      <Card className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="rounded-lg bg-emerald-100 p-2 text-emerald-700">
            <PackageCheck size={18} />
          </div>
          <div>
            <div className="font-medium text-slate-900">Next collection</div>
            <div className="text-sm text-slate-500">
              {assignments.length > 0 ? `${assignments[0].passport_number} / ${assignments[0].priority} / ${assignments[0].facility_name || 'Facility'}` : 'No active collection queued'}
            </div>
          </div>
        </div>
        <div className="text-sm text-slate-500">{assignments.length > 0 ? 'Checklist ready' : 'Awaiting assignment'}</div>
      </Card>
    </div>
  );
}
