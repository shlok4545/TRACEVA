import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, FileText, MapPin, AlertTriangle, Weight, QrCode, Clock, Truck, Stethoscope, CheckCircle2, Plus } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';
import { api, type WastePassport } from '../../services/api';

function statusTone(status: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const value = String(status || '').toUpperCase();
  if (value === 'COMPLETED' || value === 'VERIFIED') return 'success';
  if (value === 'REJECTED') return 'danger';
  if (value === 'READY_FOR_PICKUP' || value === 'CLASSIFIED') return 'warning';
  if (value === 'IN_TRANSIT' || value === 'AT_TREATMENT') return 'info';
  return 'neutral';
}

function priorityTone(priority: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const p = priority.toUpperCase();
  if (p === 'CRITICAL') return 'danger';
  if (p === 'HIGH') return 'warning';
  if (p === 'MEDIUM') return 'info';
  return 'success';
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

function canRequestPickup(status: string): boolean {
  const s = status.toUpperCase();
  return ['CLASSIFIED', 'READY_FOR_PICKUP'].includes(s);
}

export function WardPassportDetailPage() {
  const { passportId } = useParams<{ passportId: string }>();
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [passport, setPassport] = useState<WastePassport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [requestingPickup, setRequestingPickup] = useState(false);
  const [pickupError, setPickupError] = useState<string | null>(null);
  const [pickupSuccess, setPickupSuccess] = useState(false);
  const [showQr, setShowQr] = useState(false);

  useEffect(() => {
    if (!token || !passportId) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getPassport(token, Number(passportId))
      .then((data) => {
        if (active) {
          setPassport(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load passport.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [token, passportId]);

  const handleRequestPickup = async () => {
    if (!token || !passport) return;
    setRequestingPickup(true);
    setPickupError(null);
    setPickupSuccess(false);
    try {
      await api.createPickupRequest(token, passport.id);
      setPickupSuccess(true);
      setPassport(prev => prev ? { ...prev, status: 'READY_FOR_PICKUP' } : null);
    } catch (err) {
      setPickupError(err instanceof Error ? err.message : 'Failed to request pickup.');
    } finally {
      setRequestingPickup(false);
    }
  };

  const handleGenerateQr = async () => {
    if (!token || !passport) return;
    try {
      const result = await api.generateQr(token, passport.id);
      setPassport(prev => prev ? { ...prev, qr_token: result.qr_token, qr_generated_at: result.qr_generated_at, qr_data_url: result.qr_data_url } : null);
      setShowQr(true);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate QR.');
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 py-8 px-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/ward/passports')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Loading passport...</div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 py-8 px-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/ward/passports')}>
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

  if (!passport) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 py-8 px-4">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/ward/passports')}>
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

  const items = passport.items || [];
  const firstItem = items[0];

  return (
    <div className="max-w-4xl mx-auto space-y-6 py-8 px-4 min-h-0 w-full">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/ward/passports')}>
          <ArrowLeft size={16} className="mr-1" />
          Back to Passports
        </Button>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <FileText size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Passport Detail</h2>
              <p className="text-sm text-slate-500">Digital waste traceability record</p>
            </div>
          </div>
          <StatusBadge tone={statusTone(passport.status)}>{passport.status}</StatusBadge>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <h3 className="font-medium text-slate-900 mb-2">Passport Information</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Passport ID</span><span className="font-mono font-medium text-slate-900">{passport.passport_number}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Status</span><span><StatusBadge tone={statusTone(passport.status)}>{passport.status}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Facility</span><span className="font-medium text-slate-900">{passport.facility_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Ward</span><span className="font-medium text-slate-900">{passport.ward_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Risk Priority</span><span><StatusBadge tone={priorityTone(passport.risk_priority || 'LOW')}>{passport.risk_priority || 'LOW'}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Total Weight</span><span className="font-medium text-slate-900">{passport.total_weight_kg ? `${passport.total_weight_kg.toFixed(1)} kg` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Created</span><span className="font-medium text-slate-900">{formatDate(passport.created_at)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Updated</span><span className="font-medium text-slate-900">{formatDate(passport.updated_at)}</span></div>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-900 mb-2">Waste Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Category</span><span className="font-medium text-slate-900">{firstItem?.category || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Item</span><span className="font-medium text-slate-900">{firstItem?.item_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Quantity</span><span className="font-medium text-slate-900">{firstItem?.quantity || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Weight</span><span className="font-medium text-slate-900">{firstItem?.weight_kg ? `${firstItem.weight_kg.toFixed(1)} kg` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Source Dept</span><span className="font-medium text-slate-900">{firstItem?.source_department || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Contamination</span><span className="font-medium text-slate-900">{firstItem?.contamination_level || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Condition</span><span className="font-medium text-slate-900">{firstItem?.condition || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Segregation Group</span><span className="font-medium text-slate-900">{firstItem?.segregation_group || '—'}</span></div>
            </div>
          </div>
        </div>

        {items.length > 1 && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-2">All Items ({items.length})</h3>
            <div className="space-y-2">
              {items.map((item) => (
                <div key={item.id} className="rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Item</span><span className="font-medium text-slate-900">{item.item_name}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Qty</span><span className="font-medium text-slate-900">{item.quantity}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Weight</span><span className="font-medium text-slate-900">{item.weight_kg ? `${item.weight_kg.toFixed(1)} kg` : '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Category</span><span className="font-medium text-slate-900">{item.category || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Risk</span><span><StatusBadge tone={priorityTone(item.risk_priority || 'LOW')}>{item.risk_priority || 'LOW'}</StatusBadge></span></div>
                </div>
              ))}
            </div>
          </div>
        )}

        {passport.qr_token && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-3">QR Code</h3>
            <div className="flex items-center gap-4">
              {passport.qr_data_url && (
                <img src={passport.qr_data_url} alt="QR Code" className="w-32 h-32 border border-slate-200 bg-white p-2" />
              )}
              <div className="space-y-2 text-sm">
                <div className="flex justify-between"><span className="text-slate-500">QR Token</span><span className="font-mono text-xs text-slate-900 break-all">{passport.qr_token}</span></div>
                <div className="flex justify-between"><span className="text-slate-500">Generated</span><span className="font-medium text-slate-900">{formatDate(passport.qr_generated_at)}</span></div>
              </div>
            </div>
          </div>
        )}

        {!passport.qr_token && user?.role === 'WARD_STAFF' && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <Button onClick={handleGenerateQr}>
              <QrCode size={16} className="mr-2" />
              Generate QR Code
            </Button>
          </div>
        )}

        {canRequestPickup(passport.status) && user?.role === 'WARD_STAFF' && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-3">Request Pickup</h3>
            {pickupSuccess && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 mb-3">
                <div className="flex items-center gap-2 text-emerald-700">
                  <CheckCircle2 size={20} />
                  <span className="font-semibold">Pickup requested successfully</span>
                </div>
                <p className="text-sm text-emerald-600 mt-1">Passport status updated to READY_FOR_PICKUP</p>
              </div>
            )}
            {pickupError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 mb-3">
                {pickupError}
              </div>
            )}
            <Button onClick={handleRequestPickup} disabled={requestingPickup || pickupSuccess}>
              <Plus size={16} className="mr-2" />
              {requestingPickup ? 'Requesting...' : 'Request Pickup'}
            </Button>
            <p className="text-xs text-slate-500 mt-2">Creates a pickup request and changes passport status to READY_FOR_PICKUP</p>
          </div>
        )}

        {passport.status === 'READY_FOR_PICKUP' && !canRequestPickup(passport.status) && (
          <div className="mt-4 pt-4 border-t border-slate-200 text-center text-slate-500">
            <Truck size={24} className="mx-auto mb-2 opacity-40" />
            <p>Pickup already requested. Awaiting collector assignment.</p>
          </div>
        )}

        {['IN_TRANSIT', 'AT_TREATMENT', 'COMPLETED', 'REJECTED'].includes(passport.status) && (
          <div className="mt-4 pt-4 border-t border-slate-200 text-center text-slate-500">
            <Stethoscope size={24} className="mx-auto mb-2 opacity-40" />
            <p>This passport has progressed beyond the pickup phase (status: {passport.status}).</p>
          </div>
        )}
      </Card>
    </div>
  );
}