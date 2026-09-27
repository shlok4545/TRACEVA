import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { PackageOpen, Eye, CheckCircle2, XCircle } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api, type ReceivingQueueItem } from '../../services/api';

function toneForStatus(status: string) {
  const value = String(status || '').toUpperCase();
  if (value.includes('REJECTED') || value.includes('ESCALATED')) return 'danger';
  if (value.includes('PENDING') || value.includes('VALIDATING')) return 'warning';
  if (value.includes('RECEIVED') || value.includes('COMPLETED') || value === 'AT_TREATMENT') return 'success';
  return 'neutral';
}

export function FacilityReceivingPage() {
  const { token } = useAuth();
  const navigate = useNavigate();
  const [rows, setRows] = useState<ReceivingQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getReceivingQueue(token)
      .then((data) => {
        if (active) setRows(data);
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load receiving queue.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token]);

  const handleAccept = async (item: ReceivingQueueItem) => {
    const weight = prompt(`Enter received weight (kg) for ${item.passport_number}:`, String(item.total_weight_kg || ''));
    if (weight === null) return;
    const sealInput = prompt('Seal condition (INTACT, DAMAGED, LEAKING, UNKNOWN):', 'INTACT');
    if (sealInput === null) return;
    const seal = sealInput.toUpperCase();
    const notesInput = prompt('Receiving notes (optional):', '');
    const notes = notesInput?.trim() || undefined;
    try {
      await api.acceptReceiving(token, item.passport_id, {
        received_weight_kg: Number(weight) || 0,
        seal_condition: seal,
        notes,
      });
      setRows((prev) => prev.map((r) => (r.passport_id === item.passport_id ? { ...r, status: 'AT_TREATMENT', seal_condition: seal } : r)));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to accept');
    }
  };

  const handleReject = async (item: ReceivingQueueItem) => {
    const reasonInput = prompt(`Reject ${item.passport_number}? Enter reason:`);
    if (reasonInput === null || !reasonInput.trim()) return;
    const reason = reasonInput.trim();
    try {
      await api.rejectReceiving(token, item.passport_id, { reason });
      setRows((prev) => prev.filter((r) => r.passport_id !== item.passport_id));
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject');
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Facility receiving</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Receiving Queue</h1>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <PackageOpen size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Inbound waste</h2>
              <p className="text-sm text-slate-500">Receipts waiting for intake validation</p>
            </div>
          </div>
          <Badge variant="info">{rows.length} batches</Badge>
        </div>

        {loading && <div className="text-sm text-slate-500">Loading receiving queue...</div>}
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <Table
            headers={['Passport', 'Source Facility', 'Ward', 'Category', 'Weight', 'Risk', 'Transport', 'Status', 'Actions']}
            rows={rows.map((item) => [
              <Link to={`/facility/receiving/${item.passport_id}`} className="font-mono text-slate-900 hover:underline">{item.passport_number}</Link>,
              item.facility_name || '—',
              item.ward_name || '—',
              item.waste_category || '—',
              item.total_weight_kg ? `${item.total_weight_kg.toFixed(1)} kg` : '—',
              <StatusBadge key={item.passport_id} tone={toneForStatus(item.risk_priority || 'LOW')}>{item.risk_priority || 'LOW'}</StatusBadge>,
              item.transport_status || '—',
              <StatusBadge tone={toneForStatus(item.status)}>{item.status}</StatusBadge>,
              <div className="flex items-center gap-2">
                <Link to={`/facility/receiving/${item.passport_id}`}>
                  <Button variant="ghost" size="sm" aria-label="View details">
                    <Eye size={14} />
                  </Button>
                </Link>
                {item.status === 'IN_TRANSIT' && (
                  <>
                    <Button variant="secondary" size="sm" onClick={() => handleAccept(item)}>
                      <CheckCircle2 size={14} className="mr-1" />
                      Accept
                    </Button>
                    <Button variant="ghost" size="sm" onClick={() => handleReject(item)}>
                      <XCircle size={14} className="mr-1" />
                      Reject
                    </Button>
                  </>
                )}
              </div>,
            ])}
          />
        )}

        {!loading && !error && rows.length === 0 && (
          <div className="text-center text-slate-500 py-8">No inbound waste awaiting receipt.</div>
        )}
      </Card>
    </div>
  );
}