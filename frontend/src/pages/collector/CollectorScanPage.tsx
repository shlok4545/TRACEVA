import { useEffect, useRef, useState, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Camera, QrCode, AlertCircle, CheckCircle2, Loader2, Eye, EyeOff, PackageOpen, Truck } from 'lucide-react';
import { Html5Qrcode } from 'html5-qrcode';

import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

type ScanPhase = 'idle' | 'validating' | 'validated' | 'verifying' | 'matched' | 'handover' | 'transport' | 'arrival' | 'error';
type ScanMode = 'camera' | 'manual';

type Assignment = {
  id: number;
  passport_id: number;
  passport_number: string;
  facility_name?: string | null;
  ward_name?: string | null;
  priority: string;
  risk_score_snapshot?: number | null;
  status: string;
  requested_at?: string | null;
  created_at?: string | null;
  waiting_minutes?: number;
  due_at?: string | null;
  notes?: string | null;
};

type QrValidationResult = {
  passport_number: string;
  status: string;
  facility_id: number;
  facility_name: string | null;
  ward_id: number | null;
  ward_name: string | null;
  risk_priority: string | null;
  waste_category: string | null;
  total_weight_kg: number | null;
  message: string;
};

const priorityTone = (priority: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
  const p = priority.toUpperCase();
  if (p === 'CRITICAL') return 'danger';
  if (p === 'HIGH') return 'warning';
  if (p === 'MEDIUM') return 'info';
  return 'success';
};

const statusTone = (status: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' => {
  const s = status.toUpperCase();
  if (s === 'COMPLETED' || s === 'VERIFIED') return 'success';
  if (s === 'IN_TRANSIT' || s === 'AT_TREATMENT' || s === 'IN_PROGRESS') return 'info';
  if (s === 'READY_FOR_PICKUP' || s === 'ASSIGNED' || s === 'ACCEPTED' || s === 'CLASSIFIED') return 'warning';
  if (s === 'REJECTED' || s === 'CANCELLED') return 'danger';
  return 'neutral';
};

function formatWeight(kg: number | null): string {
  if (kg === null || kg === undefined) return '—';
  return `${kg.toFixed(1)} kg`;
}

function formatError(err: unknown): string {
  if (err instanceof Error) {
    const msg = err.message;
    if (msg.startsWith('401') || msg.includes('Unauthorized')) return 'Session expired. Please sign in again.';
    if (msg.includes('NetworkError') || msg.includes('Failed to fetch')) return 'Network error — cannot reach backend.';
    return msg.replace(/"/g, '');
  }
  return 'An unexpected error occurred.';
}

export function CollectorScanPage() {
  const { token, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const html5QrRef = useRef<Html5Qrcode | null>(null);
  const readerElementRef = useRef<HTMLDivElement>(null);

  const pickupIdParam = searchParams.get('pickupId');
  const initialPickupId = pickupIdParam ? Number(pickupIdParam) : null;

  const [assignments, setAssignments] = useState<Assignment[]>([]);
  const [loadingAssignments, setLoadingAssignments] = useState(true);
  const [pickupId, setPickupId] = useState<number | null>(initialPickupId);
  const [mode, setMode] = useState<ScanMode>('camera');
  const [phase, setPhase] = useState<ScanPhase>('idle');
  const [qrToken, setQrToken] = useState('');
  const [validation, setValidation] = useState<QrValidationResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showToken, setShowToken] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [cameraPermission, setCameraPermission] = useState<'prompt' | 'granted' | 'denied'>('prompt');
  const [activeCameraId, setActiveCameraId] = useState<string>('');
  const [availableCameras, setAvailableCameras] = useState<Array<{ id: string; label: string }>>([]);

  useEffect(() => {
    async function loadAssignments() {
      if (!token || !user || user.role !== 'COLLECTOR') return;
      setLoadingAssignments(true);
      try {
        const data = await api.getCollectorAssignments(token);
        const active = data.filter((a) => !['COLLECTED', 'CANCELLED'].includes(a.status.toUpperCase()));
        setAssignments(active);
        if (!pickupId && active.length > 0) {
          setPickupId(active[0].id);
        }
      } catch (err) {
        setError(formatError(err));
      } finally {
        setLoadingAssignments(false);
      }
    }
    loadAssignments();
  }, [token, user, pickupId]);

  useEffect(() => {
    if (!pickupId) return;
    setPhase('idle');
    setValidation(null);
    setError(null);
    setQrToken('');
    stopCamera();
  }, [pickupId]);

  async function initCameras() {
    try {
      const cameras = await Html5Qrcode.getCameras();
      if (cameras.length > 0) {
        setAvailableCameras(cameras.map((c) => ({ id: c.id, label: c.label || `Camera ${c.id}` })));
        setActiveCameraId(cameras[0].id);
        setCameraPermission('granted');
      }
    } catch {
      setCameraPermission('denied');
    }
  }

  async function startCamera() {
    if (isCameraLoading || !html5QrRef.current || !readerElementRef.current) return;
    setIsCameraLoading(true);
    setError(null);
    try {
      await html5QrRef.current.start(
        activeCameraId,
        {
          fps: 10,
          qrbox: { width: 250, height: 250 },
          aspectRatio: 1,
        },
        onScanSuccess,
        onScanError
      );
      setCameraPermission('granted');
    } catch (err) {
      const msg = formatError(err);
      setCameraPermission('denied');
      if (!msg.includes('permission') && !msg.includes('denied')) {
        setError(`Camera error: ${msg}`);
      }
    } finally {
      setIsCameraLoading(false);
    }
  }

  async function stopCamera() {
    if (html5QrRef.current) {
      try {
        await html5QrRef.current.stop();
      } catch {
      }
      html5QrRef.current.clear();
      html5QrRef.current = null;
    }
  }

  useEffect(() => {
    if (mode === 'camera' && readerElementRef.current && !html5QrRef.current) {
      html5QrRef.current = new Html5Qrcode(readerElementRef.current.id);
      initCameras().then(() => {
        if (mode === 'camera' && cameraPermission !== 'denied') {
          startCamera();
        }
      });
    }
    return () => {
      stopCamera();
    };
  }, [mode, cameraPermission]);

  const onScanSuccess = useCallback((decodedText: string) => {
    if (decodedText && decodedText !== qrToken) {
      setQrToken(decodedText);
      handleToken(decodedText);
    }
  }, [qrToken]);

  const onScanError = useCallback(() => {
  }, []);

  async function handleToken(tokenValue: string) {
    if (!token) return;
    setPhase('validating');
    setError(null);
    try {
      const result = await api.validateQrToken(tokenValue);
      setValidation(result);
      setPhase('validated');
    } catch (err) {
      setError(formatError(err));
      setPhase('error');
    }
  }

  async function handleVerifyAssignment() {
    if (!token || !pickupId || !validation) return;
    setPhase('verifying');
    setError(null);
    try {
      await api.scanPickupQr(token, pickupId, validation.passport_number);
      setPhase('matched');
    } catch (err) {
      const msg = formatError(err);
      if (msg.includes('does not match') || msg.includes('assignment')) {
        setError('Passport does not match this pickup assignment.');
      } else {
        setError(msg);
      }
      setPhase('error');
    }
  }

  function handleManualSubmit() {
    if (qrToken.trim()) {
      handleToken(qrToken.trim());
    }
  }

  function handleRetry() {
    setPhase('idle');
    setValidation(null);
    setError(null);
  }

  function handleClearPickup() {
    setPickupId(null);
    setPhase('idle');
    setValidation(null);
    setError(null);
    setSearchParams({});
  }

  const [handoverChecklist, setHandoverChecklist] = useState<Record<string, boolean>>({
    bag_identity_verified: false,
    qr_scan_successful: false,
    category_verified: false,
    seal_condition_verified: false,
    weight_verified: false,
    ppe_verified: false,
  });
  const [sealCondition, setSealCondition] = useState<'INTACT' | 'DAMAGED' | 'LEAKING' | 'UNKNOWN'>('INTACT');
  const [handoverNotes, setHandoverNotes] = useState('');
  const [handoverError, setHandoverError] = useState<string | null>(null);

  const [transportId, setTransportId] = useState<number | null>(null);
  const [transportRecord, setTransportRecord] = useState<{ id: number; pickup_id: number; passport_id: number; event_type: string; vehicle_number: string; from_facility_id: number; to_facility_id: number | null; departure_time: string; seal_status: string; notes: string | null; created_at: string } | null>(null);
  const [vehicleNumber, setVehicleNumber] = useState('');
  const [transportSealCondition, setTransportSealCondition] = useState<'INTACT' | 'DAMAGED' | 'LEAKING' | 'UNKNOWN'>('INTACT');
  const [transportNotes, setTransportNotes] = useState('');
  const [transportError, setTransportError] = useState<string | null>(null);
  const [arrivalError, setArrivalError] = useState<string | null>(null);

  async function handleStartHandover() {
    setPhase('handover');
    setHandoverChecklist({
      bag_identity_verified: false,
      qr_scan_successful: true,
      category_verified: false,
      seal_condition_verified: false,
      weight_verified: false,
      ppe_verified: false,
    });
    setSealCondition('INTACT');
    setHandoverNotes('');
    setHandoverError(null);
  }

  async function handleSubmitHandover() {
    if (!token || !pickupId) return;
    const missing = Object.entries(handoverChecklist).filter(([, v]) => !v).map(([k]) => k);
    if (missing.length > 0) {
      setHandoverError(`Missing mandatory checklist items: ${missing.join(', ')}.`);
      return;
    }
    if ((sealCondition === 'DAMAGED' || sealCondition === 'LEAKING') && !handoverNotes.trim()) {
      setHandoverError('A note is required when seal condition is damaged or leaking.');
      return;
    }
    setHandoverError(null);
    try {
      await api.confirmHandover(token, pickupId, {
        seal_condition: sealCondition,
        notes: handoverNotes || undefined,
        checklist: handoverChecklist,
      });
      setPhase('matched');
    } catch (err) {
      setHandoverError(formatError(err));
    }
  }

  function handleBackFromHandover() {
    setPhase('matched');
    setHandoverError(null);
  }

  async function handleStartTransport() {
    if (!token || !pickupId) return;
    setPhase('transport');
    setTransportError(null);
    try {
      const result = await api.startTransport(token, pickupId, {
        vehicle_number: vehicleNumber || undefined,
        seal_condition: transportSealCondition,
        notes: transportNotes || undefined,
      });
      setTransportId(result.id);
      setTransportRecord(result);
    } catch (err) {
      setTransportError(formatError(err));
      setPhase('handover');
    }
  }

  async function handleMarkArrival() {
    if (!token || !transportId) return;
    setPhase('arrival');
    setArrivalError(null);
    try {
      await api.markTransportArrival(token, transportId, {
        to_facility_id: 4,
      });
      setPhase('matched');
      setTransportRecord((prev) => prev ? { ...prev, event_type: 'TRANSPORT_ARRIVED', arrival_time: new Date().toISOString() } : null);
    } catch (err) {
      setArrivalError(formatError(err));
      setPhase('transport');
    }
  }

  function formatDate(iso: string | null | undefined): string {
    if (!iso) return '—';
    try {
      return new Date(iso).toLocaleString();
    } catch {
      return iso;
    }
  }

  const currentAssignment = assignments.find((a) => a.id === pickupId);

  if (!token || !user || user.role !== 'COLLECTOR') {
    return (
      <div className="max-w-sm mx-auto space-y-6 py-8 px-4">
        <Card>
          <div className="text-center text-slate-600 py-4">Collector session required.</div>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-sm mx-auto space-y-6 py-8 px-4">
      <div className="text-center">
        <h1 className="text-2xl font-semibold text-slate-900">SCAN TRACEVA PASSPORT</h1>
        <p className="mt-1 text-sm text-slate-500">Verify waste bag QR against active assignment</p>
      </div>

      {loadingAssignments && (
        <Card>
          <div className="text-center text-slate-500 py-4">Loading assignments…</div>
        </Card>
      )}

      {!pickupId && !loadingAssignments && (
        <Card>
          <h2 className="text-lg font-semibold text-slate-900 mb-4">Select Assignment</h2>
          {assignments.length === 0 ? (
            <div className="text-center text-slate-500 py-4">No active pickup assignments.</div>
          ) : (
            <div className="space-y-2">
              {assignments.map((a) => (
                <Button
                  key={a.id}
                  variant="secondary"
                  className="w-full justify-start gap-3"
                  onClick={() => {
                    setPickupId(a.id);
                    setSearchParams({ pickupId: String(a.id) });
                  }}
                >
                  <div className="flex-1 text-left">
                    <div className="font-medium text-slate-900">{a.passport_number}</div>
                    <div className="text-xs text-slate-500">{a.facility_name} · {a.ward_name || 'No ward'}</div>
                  </div>
                  <StatusBadge tone={priorityTone(a.priority)}>{a.priority}</StatusBadge>
                </Button>
              ))}
            </div>
          )}
        </Card>
      )}

      {pickupId && !loadingAssignments && currentAssignment && (
        <>
          <Card>
            <div className="mb-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
                  <PackageOpen size={18} />
                </div>
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">Active Assignment</h2>
                  <p className="text-sm text-slate-500">Scan passport for this pickup</p>
                </div>
              </div>
              <Badge variant="info">{currentAssignment.priority}</Badge>
            </div>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Passport</span><span className="font-medium text-slate-900">{currentAssignment.passport_number}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Facility</span><span className="font-medium text-slate-900">{currentAssignment.facility_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Ward</span><span className="font-medium text-slate-900">{currentAssignment.ward_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Status</span><span><StatusBadge tone={statusTone(currentAssignment.status)}>{currentAssignment.status}</StatusBadge></span></div>
            </div>
            <Button variant="ghost" size="sm" className="mt-2 w-full justify-start" onClick={handleClearPickup}>
              <Truck size={14} className="mr-2" />
              Change Assignment
            </Button>
          </Card>

          <Card>
            <div className="mb-4 flex gap-2">
              <Button
                variant={mode === 'camera' ? 'primary' : 'secondary'}
                onClick={() => setMode('camera')}
                disabled={phase === 'validating' || phase === 'verifying'}
              >
                <Camera size={16} className="mr-2" />
                Camera
              </Button>
              <Button
                variant={mode === 'manual' ? 'primary' : 'secondary'}
                onClick={() => setMode('manual')}
                disabled={phase === 'validating' || phase === 'verifying'}
              >
                <QrCode size={16} className="mr-2" />
                Manual
              </Button>
            </div>

            {mode === 'camera' && (
              <div className="space-y-4">
                {cameraPermission === 'denied' ? (
                  <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-700 text-center">
                    <AlertCircle size={20} className="mx-auto mb-2" />
                    <div className="font-medium">Camera access denied</div>
                    <div className="mt-1">Enable camera permission in browser settings, or use Manual entry.</div>
                  </div>
                ) : (
                  <>
                    <div className="relative rounded-lg bg-slate-100 overflow-hidden">
                      <div ref={readerElementRef} id="qr-reader" className="w-full aspect-square min-h-[280px]" />
                      {phase === 'validating' && (
                        <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                          <Loader2 size={32} className="text-white animate-spin" />
                        </div>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 text-center">Point camera at QR code on waste bag</p>
                  </>
                )}
              </div>
            )}

            {mode === 'manual' && (
              <div className="space-y-4">
                <Input
                  label="QR Token / Passport Token"
                  type="text"
                  value={qrToken}
                  onChange={(e) => setQrToken(e.target.value)}
                  placeholder="Paste or type QR token here"
                  disabled={phase === 'validating' || phase === 'verifying'}
                />
                <div className="flex items-center gap-2">
                  <Button onClick={handleManualSubmit} disabled={phase === 'validating' || phase === 'verifying' || !qrToken.trim()}>
                    Verify Token
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setShowToken(!showToken)} disabled={phase === 'validating' || phase === 'verifying'}>
                    {showToken ? <EyeOff size={16} /> : <Eye size={16} />}
                  </Button>
                </div>
              </div>
            )}

            {error && phase === 'error' && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <AlertCircle size={16} className="inline mr-1" />
                {error}
              </div>
            )}

            {phase === 'validated' && validation && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3">
                <div className="flex items-center gap-2 text-emerald-700">
                  <CheckCircle2 size={20} />
                  <span className="font-semibold">VALID TRACEVA PASSPORT</span>
                </div>
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Passport ID</span><span className="font-mono font-medium text-slate-900">{validation.passport_number}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Waste Category</span><span className="font-medium text-slate-900">{validation.waste_category || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Risk / Priority</span><span><StatusBadge tone={priorityTone(validation.risk_priority || 'LOW')}>{validation.risk_priority || 'LOW'}</StatusBadge></span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Facility</span><span className="font-medium text-slate-900">{validation.facility_name || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Ward</span><span className="font-medium text-slate-900">{validation.ward_name || '—'}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Weight</span><span className="font-medium text-slate-900">{formatWeight(validation.total_weight_kg)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Current Status</span><span><StatusBadge tone={statusTone(validation.status)}>{validation.status}</StatusBadge></span></div>
                </div>
                <Button className="w-full" onClick={handleVerifyAssignment}>
                  Verify Assignment
                </Button>
              </div>
            )}

            {phase === 'matched' && validation && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3 text-center">
                <div className="flex items-center justify-center gap-2 text-emerald-700">
                  <CheckCircle2 size={24} />
                  <span className="text-lg font-semibold">QR VERIFIED ✓</span>
                </div>
                <div className="text-sm text-slate-600">
                  Passport <span className="font-mono">{validation.passport_number}</span> matches assignment
                  <span className="font-medium">#{pickupId}</span>.
                </div>
                <div className="pt-2 border-t border-emerald-200 space-y-3">
                  <p className="text-sm text-slate-500">Complete handover to confirm collection.</p>
                  <Button size="lg" className="w-full" onClick={handleStartHandover}>
                    <Truck size={16} className="mr-2" />
                    Continue to Handover
                  </Button>
                  {transportRecord && transportRecord.event_type === 'TRANSPORT_STARTED' && (
                    <div className="pt-2 border-t border-emerald-200">
                      <p className="text-sm text-slate-500 mb-2">Transport in progress</p>
                      <Button size="lg" className="w-full" onClick={() => setPhase('transport')}>
                        <Truck size={16} className="mr-2" />
                        View Transport
                      </Button>
                    </div>
                  )}
                  {!transportRecord && currentAssignment?.status === 'COLLECTED' && (
                    <div className="pt-2 border-t border-emerald-200">
                      <p className="text-sm text-slate-500 mb-2">Ready for transport</p>
                      <Button variant="secondary" size="lg" className="w-full" onClick={() => setPhase('transport')}>
                        <Truck size={16} className="mr-2" />
                        Start Transport
                      </Button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {phase === 'handover' && validation && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">Handover Checklist</h3>
                  <Button variant="ghost" size="sm" onClick={handleBackFromHandover}>
                    Back
                  </Button>
                </div>
                <p className="text-sm text-slate-500">Verify all items before confirming collection.</p>
                {handoverError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle size={16} className="inline mr-1" />
                    {handoverError}
                  </div>
                )}
                <div className="space-y-2">
                  {Object.entries(handoverChecklist).map(([key, checked]) => (
                    <label key={key} className="flex items-center gap-3 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={(e) => setHandoverChecklist({ ...handoverChecklist, [key]: e.target.checked })}
                        className="rounded border-slate-300 text-slate-900 focus:ring-slate-500"
                      />
                      <span className="text-slate-700 capitalize">{key.replace(/_/g, ' ')}</span>
                    </label>
                  ))}
                </div>
                <div className="space-y-2 pt-2 border-t border-slate-200">
                  <label className="block text-sm font-medium text-slate-700">Seal Condition</label>
                  <select
                    value={sealCondition}
                    onChange={(e) => setSealCondition(e.target.value as typeof sealCondition)}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-500"
                  >
                    <option value="INTACT">INTACT</option>
                    <option value="DAMAGED">DAMAGED</option>
                    <option value="LEAKING">LEAKING</option>
                    <option value="UNKNOWN">UNKNOWN</option>
                  </select>
                  {(sealCondition === 'DAMAGED' || sealCondition === 'LEAKING') && (
                    <div className="space-y-2">
                      <label className="block text-sm font-medium text-slate-700">Notes (required)</label>
                      <textarea
                        value={handoverNotes}
                        onChange={(e) => setHandoverNotes(e.target.value)}
                        rows={3}
                        className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-500"
                        placeholder="Describe seal condition issue..."
                      />
                    </div>
                  )}
                </div>
                <div className="flex gap-2 pt-2">
                  <Button variant="secondary" className="flex-1" onClick={handleBackFromHandover}>
                    Cancel
                  </Button>
                  <Button className="flex-1" onClick={handleSubmitHandover}>
                    Confirm Handover
                  </Button>
                </div>
              </div>
            )}

            {phase === 'transport' && validation && transportRecord && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-4">
                <div className="flex items-center justify-center gap-2 text-emerald-700">
                  <Truck size={24} />
                  <span className="text-lg font-semibold">TRANSPORT STARTED</span>
                </div>
                <div className="grid gap-2 text-sm">
                  <div className="flex justify-between"><span className="text-slate-500">Vehicle</span><span className="font-medium text-slate-900">{transportRecord.vehicle_number}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Seal Status</span><span className="font-medium text-slate-900">{transportRecord.seal_status}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">Departure</span><span className="font-medium text-slate-900">{formatDate(transportRecord.departure_time)}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">From Facility</span><span className="font-medium text-slate-900">{transportRecord.from_facility_id}</span></div>
                  <div className="flex justify-between"><span className="text-slate-500">To Facility</span><span className="font-medium text-slate-900">{transportRecord.to_facility_id || '—'}</span></div>
                </div>
                {transportError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle size={16} className="inline mr-1" />
                    {transportError}
                  </div>
                )}
                <Button size="lg" className="w-full" onClick={handleMarkArrival}>
                  <CheckCircle2 size={16} className="mr-2" />
                  Arrived at Treatment Facility
                </Button>
              </div>
            )}

            {phase === 'transport' && validation && !transportRecord && (
              <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-slate-900">Start Transport</h3>
                  <Button variant="ghost" size="sm" onClick={() => setPhase('matched')}>
                    Back
                  </Button>
                </div>
                <p className="text-sm text-slate-500">Record transport departure details.</p>
                {transportError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle size={16} className="inline mr-1" />
                    {transportError}
                  </div>
                )}
                <Input label="Vehicle Number" value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)} placeholder="e.g., MH-12-TRV-01" />
                <Select label="Seal Condition" value={transportSealCondition} onChange={(e) => setTransportSealCondition(e.target.value as typeof transportSealCondition)}>
                  <option value="INTACT">INTACT</option>
                  <option value="DAMAGED">DAMAGED</option>
                  <option value="LEAKING">LEAKING</option>
                  <option value="UNKNOWN">UNKNOWN</option>
                </Select>
                <Input label="Notes (optional)" value={transportNotes} onChange={(e) => setTransportNotes(e.target.value)} placeholder="Additional notes..." />
                <div className="flex gap-2 pt-2">
                  <Button variant="secondary" className="flex-1" onClick={() => setPhase('matched')}>
                    Cancel
                  </Button>
                  <Button className="flex-1" onClick={handleStartTransport}>
                    <Truck size={16} className="mr-2" />
                    Start Transport
                  </Button>
                </div>
              </div>
            )}

            {phase === 'arrival' && validation && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3 text-center">
                <div className="flex items-center justify-center gap-2 text-emerald-700">
                  <Loader2 size={24} className="animate-spin" />
                  <span className="text-lg font-semibold">ARRIVING AT TREATMENT FACILITY</span>
                </div>
                {arrivalError && (
                  <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                    <AlertCircle size={16} className="inline mr-1" />
                    {arrivalError}
                  </div>
                )}
                <div className="text-sm text-slate-600">
                  Recording arrival at treatment facility...
                </div>
              </div>
            )}

            {phase === 'idle' && !validation && !error && (
              <div className="text-center text-slate-500 py-6">
                <QrCode size={32} className="mx-auto mb-2 opacity-40" />
                <p>Scan or enter QR token to begin verification</p>
              </div>
            )}
          </Card>
        </>
      )}

      {pickupId && !loadingAssignments && !currentAssignment && (
        <Card>
          <div className="text-center text-rose-600 py-4">
            <AlertCircle size={24} className="mx-auto mb-2" />
            <p className="font-medium">Assignment not found</p>
            <p className="text-sm text-slate-500 mt-1">This pickup may have been completed or reassigned.</p>
            <Button variant="secondary" className="mt-3" onClick={handleClearPickup}>
              Back to Assignments
            </Button>
          </div>
        </Card>
      )}
    </div>
  );
}