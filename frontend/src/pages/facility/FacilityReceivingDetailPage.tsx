import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, PackageOpen, Shield, AlertCircle, CheckCircle2, XCircle, Clock, User, MapPin, Weight } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';
import { api, type ReceivingDetail } from '../../services/api';

function toneForStatus(status: string) {
  const value = String(status || '').toUpperCase();
  if (value.includes('REJECTED') || value.includes('ESCALATED')) return 'danger';
  if (value.includes('PENDING') || value.includes('VALIDATING')) return 'warning';
  if (value.includes('RECEIVED') || value.includes('COMPLETED') || value === 'AT_TREATMENT') return 'success';
  return 'neutral';
}

function FacilityReceivingDetailPage() {
  const { passportId } = useParams<{ passportId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [detail, setDetail] = useState<ReceivingDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [receivedWeight, setReceivedWeight] = useState('');
  const [sealCondition, setSealCondition] = useState<'INTACT' | 'DAMAGED' | 'LEAKING' | 'UNKNOWN'>('INTACT');
  const [notes, setNotes] = useState('');
  const [rejectReason, setRejectReason] = useState('');

  useEffect(() => {
    if (!token || !passportId) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getReceivingDetail(token, Number(passportId))
      .then((data) => {
        if (active) {
          setDetail(data);
          if (data.total_weight_kg) setReceivedWeight(String(data.total_weight_kg));
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load receiving detail.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, passportId]);

  const handleAccept = async () => {
    if (!detail) return;
    const weight = Number(receivedWeight);
    if (!weight || weight <= 0) {
      alert('Please enter a valid received weight.');
      return;
    }
    if (!['INTACT', 'DAMAGED', 'LEAKING', 'UNKNOWN'].includes(sealCondition)) {
      alert('Please select a valid seal condition.');
      return;
    }
    if ((sealCondition === 'DAMAGED' || sealCondition === 'LEAKING') && !notes?.trim()) {
      alert('Notes are required when seal condition is DAMAGED or LEAKING.');
      return;
    }
    const notesValue = notes?.trim() || '';
    setSubmitting(true);
    try {
      await api.acceptReceiving(token, detail.passport_id, {
        received_weight_kg: weight,
        seal_condition: sealCondition,
        notes: notesValue || undefined,
      });
      navigate('/facility/receiving');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to accept');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReject = async () => {
    if (!detail || !rejectReason?.trim()) {
      alert('Please enter a rejection reason.');
      return;
    }
    const reason = rejectReason.trim();
    setSubmitting(true);
    try {
      await api.rejectReceiving(token, detail.passport_id, { reason });
      navigate('/facility/receiving');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to reject');
    } finally {
      setSubmitting(false);
    }
  }

  const latestEvent = detail?.events?.[0];

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/receiving')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Loading receiving detail...</div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/receiving')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>
        </Card>
      </div>
    );
  }

  if (!detail) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/receiving')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Passport not found.</div>
        </Card>
      </div>
    );
  }

  const item = detail.items?.[0];
  const category = item?.category || detail.waste_category || '—';
  const sourceDept = item?.source_department || '—';
  const contamination = item?.contamination_level || '—';

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/facility/receiving')}>
          <ArrowLeft size={16} className="mr-1" />
          Back to Queue
        </Button>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <PackageOpen size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Receiving Detail</h2>
              <p className="text-sm text-slate-500">Validate and record inbound waste</p>
            </div>
          </div>
          <Badge variant="info">{detail.status}</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="font-medium text-slate-900 mb-2">Passport Information</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Passport ID</span><span className="font-mono font-medium text-slate-900">{detail.passport_number}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Source Facility</span><span className="font-medium text-slate-900">{detail.facility_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Ward</span><span className="font-medium text-slate-900">{detail.ward_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Waste Category</span><span className="font-medium text-slate-900">{category}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Source Department</span><span className="font-medium text-slate-900">{sourceDept}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Contamination Level</span><span className="font-medium text-slate-900">{contamination}</span></div>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-900 mb-2">Measurements & Risk</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Total Weight</span><span className="font-medium text-slate-900">{detail.total_weight_kg ? `${detail.total_weight_kg.toFixed(1)} kg` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Risk / Priority</span><span><StatusBadge tone={toneForStatus(detail.risk_priority || 'LOW')}>{detail.risk_priority || 'LOW'}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Current Status</span><span><StatusBadge tone={toneForStatus(detail.status)}>{detail.status}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Transport Status</span><span className="font-medium text-slate-900">{detail.transport_status || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Treatment Status</span><span className="font-medium text-slate-900">{detail.treatment_status || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Last Received</span><span className="font-medium text-slate-900">{detail.received_at ? new Date(detail.received_at).toLocaleString() : '—'}</span></div>
            </div>
          </div>
        </div>

        {detail.items && detail.items.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-2">Waste Items</h3>
            <div className="space-y-2">
              {detail.items.map((it) => (
                <div key={it.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Item</span><span className="font-medium text-slate-900">{it.item_name}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Quantity</span><span className="font-medium text-slate-900">{it.quantity}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Weight</span><span className="font-medium text-slate-900">{it.weight_kg ? `${it.weight_kg.toFixed(1)} kg` : '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Category</span><span className="font-medium text-slate-900">{it.category || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Segregation</span><span className="font-medium text-slate-900">{it.segregation_group || '—'}</span></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.events && detail.events.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-2">Chain of Custody</h3>
            <div className="space-y-2">
              {detail.events.map((ev) => (
                <div key={ev.id} className="flex items-start gap-3 text-sm">
                  <div className="rounded-full bg-slate-100 p-1.5"><Clock size={12} className="text-slate-500" /></div>
                  <div className="flex-1">
                    <div className="font-medium text-slate-900">{ev.event_type}</div>
                    <div className="text-slate-600">{ev.details || ''}</div>
                    <div className="text-xs text-slate-500">{ev.actor_name || 'System'} · {ev.created_at ? new Date(ev.created_at).toLocaleString() : ''}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {detail.status === 'IN_TRANSIT' && (
          <div className="mt-6 pt-4 border-t border-slate-200 space-y-4">
            <h3 className="font-medium text-slate-900">Intake Verification</h3>

            <div className="grid gap-4 md:grid-cols-3">
              <Input label="Received Weight (kg)" type="number" step="0.1" min="0" value={receivedWeight} onChange={(e) => setReceivedWeight(e.target.value)} placeholder="0.0" />
              <Select label="Seal Condition" value={sealCondition} onChange={(e) => setSealCondition(e.target.value as typeof sealCondition)}>
                <option value="INTACT">INTACT</option>
                <option value="DAMAGED">DAMAGED</option>
                <option value="LEAKING">LEAKING</option>
                <option value="UNKNOWN">UNKNOWN</option>
              </Select>
              <div />
            </div>

            {(sealCondition === 'DAMAGED' || sealCondition === 'LEAKING') && (
              <Input label="Notes (required for DAMAGED/LEAKING)" value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="Describe the seal condition issue..." />
            )}

            <div className="flex gap-3">
              <Button onClick={handleAccept} disabled={submitting} className="flex-1">
                <CheckCircle2 size={16} className="mr-2" />
                {submitting ? 'Accepting...' : 'Accept & Record Receipt'}
              </Button>
              <Button variant="secondary" onClick={() => setRejectReason(prompt('Rejection reason:') || '')} disabled={submitting} className="flex-1">
                <XCircle size={16} className="mr-2" />
                Reject
              </Button>
            </div>

            {rejectReason && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <AlertCircle size={16} className="inline mr-1" />
                Rejection reason: {rejectReason}
                <Button variant="ghost" size="sm" className="ml-2" onClick={() => setRejectReason('')}>Clear</Button>
              </div>
            )}
          </div>
        )}

        {detail.status !== 'IN_TRANSIT' && (
          <div className="mt-6 pt-4 border-t border-slate-200 text-center text-slate-500">
            <Shield size={24} className="mx-auto mb-2 opacity-40" />
            <p>This passport has already been processed (status: {detail.status}).</p>
            <Link to="/facility/treatment" className="text-sm text-slate-600 underline mt-2 inline-block">View Treatment Records →</Link>
          </div>
        )}
      </Card>
    </div>
  );
}

export { FacilityReceivingDetailPage };