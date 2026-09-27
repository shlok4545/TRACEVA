import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { ArrowLeft, Stethoscope, Shield, AlertCircle, CheckCircle2, XCircle, Clock, FileText, Upload, Eye, CheckCircle } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { StatusBadge } from '../../components/ui/StatusBadge';
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

export function FacilityTreatmentDetailPage() {
  const { recordId } = useParams<{ recordId: string }>();
  const { token } = useAuth();
  const navigate = useNavigate();
  const [record, setRecord] = useState<TreatmentRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [treatmentMethod, setTreatmentMethod] = useState('');
  const [treatmentStartedAt, setTreatmentStartedAt] = useState('');
  const [treatmentCompletedAt, setTreatmentCompletedAt] = useState('');
  const [certificateNumber, setCertificateNumber] = useState('');
  const [verificationNotes, setVerificationNotes] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    if (!token || !recordId) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getTreatmentRecord(token, Number(recordId))
      .then((data) => {
        if (active) {
          setRecord(data);
          setTreatmentMethod(data.treatment_method || '');
          setTreatmentStartedAt(data.treatment_started_at || '');
          setTreatmentCompletedAt(data.treatment_completed_at || '');
          setCertificateNumber(data.certificate_number || '');
          setVerificationNotes(data.verification_notes || '');
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load treatment record.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => {
      active = false;
    };
  }, [token, recordId]);

  const handleSave = async () => {
    if (!record) return;
    setSaving(true);
    try {
      const updated = await api.updateTreatmentRecord(token, record.id, {
        treatment_method: treatmentMethod,
        treatment_started_at: treatmentStartedAt || undefined,
        treatment_completed_at: treatmentCompletedAt || undefined,
      });
      setRecord(updated);
      setTreatmentMethod(updated.treatment_method || '');
      setTreatmentStartedAt(updated.treatment_started_at || '');
      setTreatmentCompletedAt(updated.treatment_completed_at || '');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleVerify = async () => {
    if (!record) return;
    if (!record.treatment_started_at || !record.treatment_completed_at) {
      alert('Treatment start and completion timestamps are required before verification.');
      return;
    }
    setVerifying(true);
    try {
      const verified = await api.verifyTreatmentRecord(token, record.id, {
        certificate_number: certificateNumber?.trim() || undefined,
        verification_notes: verificationNotes?.trim() || undefined,
      });
      setRecord(verified);
      setCertificateNumber(verified.certificate_number || '');
      setVerificationNotes(verified.verification_notes || '');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to verify');
    } finally {
      setVerifying(false);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) setSelectedFile(file);
  };

  const handleUploadEvidence = async () => {
    if (!record || !selectedFile) return;
    if (!['application/pdf', 'image/jpeg', 'image/png'].includes(selectedFile.type)) {
      alert('Only PDF, JPG, or PNG files are allowed.');
      return;
    }
    setUploading(true);
    try {
      await api.uploadTreatmentEvidence(token, record.id, selectedFile);
      const refreshed = await api.getTreatmentRecord(token, record.id);
      setRecord(refreshed);
      setSelectedFile(null);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upload evidence');
    } finally {
      setUploading(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/treatment')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Loading treatment record...</div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/treatment')}>
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

  if (!record) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/facility/treatment')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Treatment record not found.</div>
        </Card>
      </div>
    );
  }

  const canVerify = record.verification_status !== 'VERIFIED' && record.treatment_started_at && record.treatment_completed_at;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/facility/treatment')}>
          <ArrowLeft size={16} className="mr-1" />
          Back to Records
        </Button>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <Stethoscope size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Treatment Record #{record.id}</h2>
              <p className="text-sm text-slate-500">Passport {record.passport_id} · {record.verification_status}</p>
            </div>
          </div>
          <Badge variant="info">Passport {record.passport_id}</Badge>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <h3 className="font-medium text-slate-900 mb-2">Passport & Receiving</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Passport ID</span><span className="font-mono font-medium text-slate-900">{record.passport_id}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Received At</span><span className="font-medium text-slate-900">{record.received_at ? new Date(record.received_at).toLocaleString() : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Received Weight</span><span className="font-medium text-slate-900">{record.received_weight_kg.toFixed(1)} kg</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Seal Condition</span><span><StatusBadge tone={toneForStatus(record.seal_condition)}>{record.seal_condition}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Intake Status</span><span><StatusBadge tone={toneForIntake(record.intake_status)}>{record.intake_status}</StatusBadge></span></div>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-900 mb-2">Treatment Details</h3>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Method</span><span className="font-medium text-slate-900">{record.treatment_method}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Started</span><span className="font-medium text-slate-900">{record.treatment_started_at ? new Date(record.treatment_started_at).toLocaleString() : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Completed</span><span className="font-medium text-slate-900">{record.treatment_completed_at ? new Date(record.treatment_completed_at).toLocaleString() : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Verification</span><span><StatusBadge tone={toneForStatus(record.verification_status)}>{record.verification_status}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Certificate</span><span className="font-mono font-medium text-slate-900">{record.certificate_number || '—'}</span></div>
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-900 mb-2">Verification Notes</h3>
            <div className="space-y-2 text-sm">
              {record.verification_notes ? (
                <div className="text-slate-700 whitespace-pre-wrap">{record.verification_notes}</div>
              ) : (
                <div className="text-slate-500 italic">No verification notes</div>
              )}
            </div>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <h3 className="font-medium text-slate-900 mb-4">Update Treatment</h3>
          <div className="grid gap-4 md:grid-cols-2">
            <Input label="Treatment Method" value={treatmentMethod} onChange={(e) => setTreatmentMethod(e.target.value)} placeholder="e.g., Autoclave, Incineration" />
            <Input label="Treatment Started" type="datetime-local" value={treatmentStartedAt} onChange={(e) => setTreatmentStartedAt(e.target.value)} />
            <Input label="Treatment Completed" type="datetime-local" value={treatmentCompletedAt} onChange={(e) => setTreatmentCompletedAt(e.target.value)} />
            <div />
          </div>
          <div className="mt-4 flex gap-3">
            <Button onClick={handleSave} disabled={saving}>
              <FileText size={16} className="mr-2" />
              {saving ? 'Saving...' : 'Save Treatment Record'}
            </Button>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <h3 className="font-medium text-slate-900 mb-4">Evidence</h3>
          {record.evidence && record.evidence.length > 0 ? (
            <div className="space-y-2">
              {record.evidence.map((ev) => (
                <div key={ev.id} className="flex items-center justify-between rounded-lg border border-slate-200 bg-slate-50 p-3 text-sm">
                  <div className="flex items-center gap-3">
                    <div className="rounded-full bg-slate-100 p-1.5"><FileText size={14} className="text-slate-500" /></div>
                    <div>
                      <div className="font-medium text-slate-900">{ev.file_name}</div>
                      <div className="text-xs text-slate-500">{ev.file_type} · {ev.uploaded_at ? new Date(ev.uploaded_at).toLocaleString() : ''}</div>
                    </div>
                  </div>
                  <span className="text-xs text-slate-500">{ev.description || ''}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-slate-500">No evidence uploaded yet.</p>
          )}
          <div className="mt-4 flex items-center gap-3">
            <input type="file" id="evidence-file" accept="application/pdf,image/jpeg,image/png" onChange={handleFileChange} className="sr-only" />
            <label htmlFor="evidence-file" className="cursor-pointer">
              <Button variant="secondary">
                <Upload size={16} className="mr-2" />
                Select Evidence File
              </Button>
            </label>
            {selectedFile && (
              <Button onClick={handleUploadEvidence} disabled={uploading}>
                {uploading ? <div className="w-4 h-4 border-2 border-slate-300 border-t-transparent rounded-full animate-spin" /> : 'Upload'}
              </Button>
            )}
            <span className="text-xs text-slate-500">PDF, JPG, or PNG only</span>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-slate-200">
          <h3 className="font-medium text-slate-900 mb-4">Verification</h3>
          {record.verification_status === 'VERIFIED' ? (
            <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 space-y-3 text-center">
              <div className="flex items-center justify-center gap-2 text-emerald-700">
                <CheckCircle2 size={24} />
                <span className="text-lg font-semibold">TREATMENT VERIFIED ✓</span>
              </div>
              <div className="text-sm text-slate-600">
                Certificate: <span className="font-mono">{record.certificate_number || '—'}</span>
              </div>
              <div className="text-sm text-slate-600">
                Verified at: {record.updated_at ? new Date(record.updated_at).toLocaleString() : '—'}
              </div>
              <div className="text-sm text-slate-600">
                Passport status: <span className="font-semibold text-emerald-600">COMPLETED</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              {!record.treatment_started_at && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
                  <AlertCircle size={16} className="inline mr-1" />
                  Treatment start timestamp is required before verification.
                </div>
              )}
              {!record.treatment_completed_at && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700">
                  <AlertCircle size={16} className="inline mr-1" />
                  Treatment completion timestamp is required before verification.
                </div>
              )}
              <Input label="Certificate Number (optional)" value={certificateNumber} onChange={(e) => setCertificateNumber(e.target.value)} placeholder="e.g., CERT-2026-001" />
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Verification Notes</label>
                <textarea
                  value={verificationNotes}
                  onChange={(e) => setVerificationNotes(e.target.value)}
                  rows={3}
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-500"
                  placeholder="Notes on treatment verification..."
                />
              </div>
              <Button onClick={handleVerify} disabled={verifying || !canVerify} className="w-full">
                <CheckCircle size={16} className="mr-2" />
                {verifying ? 'Verifying...' : 'Verify Treatment'}
              </Button>
              {!canVerify && !record.treatment_started_at && !record.treatment_completed_at && (
                <p className="text-xs text-slate-500 text-center">Set treatment start and completion timestamps to enable verification.</p>
              )}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}