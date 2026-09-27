import { useEffect, useState } from 'react';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, AlertTriangle, User, MapPin, PackageOpen, Clock, AlertCircle, CheckCircle2, Edit2 } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { useAuth } from '../../contexts/AuthContext';
import { api, type Incident } from '../../services/api';

function toneForSeverity(severity: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const s = severity.toUpperCase();
  if (s === 'CRITICAL') return 'danger';
  if (s === 'HIGH') return 'warning';
  if (s === 'MEDIUM') return 'info';
  if (s === 'LOW') return 'success';
  return 'neutral';
}

function toneForStatus(status: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const st = status.toUpperCase();
  if (st === 'CLOSED' || st === 'RESOLVED') return 'success';
  if (st === 'ACKNOWLEDGED' || st === 'IN_PROGRESS') return 'info';
  if (st === 'OPEN') return 'warning';
  return 'neutral';
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
}

export function AdminIncidentDetailPage() {
  const { incidentId } = useParams<{ incidentId: string }>();
  const { token, user } = useAuth();
  const navigate = useNavigate();
  const [incident, setIncident] = useState<Incident | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editSeverity, setEditSeverity] = useState<'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL'>('MEDIUM');
  const [editStatus, setEditStatus] = useState<'OPEN' | 'ACKNOWLEDGED' | 'IN_PROGRESS' | 'RESOLVED' | 'CLOSED'>('OPEN');
  const [isEditing, setIsEditing] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState('');

  useEffect(() => {
    if (!token || !incidentId) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getIncident(token, Number(incidentId))
      .then((data) => {
        if (active) {
          setIncident(data);
          setEditTitle(data.title);
          setEditDescription(data.description || '');
          setEditSeverity(data.severity as any);
          setEditStatus(data.status as any);
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load incident.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [token, incidentId]);

  const handleSave = async () => {
    if (!incident) return;
    setSaving(true);
    setActionError(null);
    try {
      await api.updateIncident(token, incident.id, {
        title: editTitle,
        description: editDescription,
        severity: editSeverity,
        status: editStatus,
      });
      const refreshed = await api.getIncident(token, incident.id);
      setIncident(refreshed);
      setIsEditing(false);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to save.');
    } finally {
      setSaving(false);
    }
  };

  const handleAcknowledge = async () => {
    if (!incident) return;
    setSaving(true);
    setActionError(null);
    try {
      const refreshed = await api.acknowledgeIncident(token, incident.id);
      setIncident(refreshed);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to acknowledge.');
    } finally {
      setSaving(false);
    }
  };

  const handleResolve = async () => {
    if (!incident) return;
    setSaving(true);
    setActionError(null);
    try {
      const refreshed = await api.resolveIncident(token, incident.id, {
        resolution_notes: resolutionNotes || undefined,
      });
      setIncident(refreshed);
      setResolutionNotes('');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to resolve.');
    } finally {
      setSaving(false);
    }
  };

  const handleClose = async () => {
    if (!incident) return;
    setSaving(true);
    setActionError(null);
    try {
      const refreshed = await api.closeIncident(token, incident.id, {
        resolution_notes: resolutionNotes || undefined,
      });
      setIncident(refreshed);
      setResolutionNotes('');
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to close.');
    } finally {
      setSaving(false);
    }
  };

  const canAcknowledge = incident && incident.status === 'OPEN';
  const canResolve = incident && (incident.status === 'ACKNOWLEDGED' || incident.status === 'IN_PROGRESS');
  const canClose = incident && incident.status === 'RESOLVED';
  const canEdit = incident && incident.status !== 'CLOSED' && user?.role === 'ADMIN';

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/incidents')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Loading incident…</div>
        </Card>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/incidents')}>
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

  if (!incident) {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate('/admin/incidents')}>
            <ArrowLeft size={16} className="mr-1" />
            Back
          </Button>
        </div>
        <Card>
          <div className="text-center text-slate-500 py-8">Incident not found.</div>
        </Card>
      </div>
    );
  }

  const isRegulator = user?.role === 'REGULATOR';
  const showActions = !isRegulator && canEdit;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate('/admin/incidents')}>
          <ArrowLeft size={16} className="mr-1" />
          Back to Incidents
        </Button>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <AlertTriangle size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Incident {incident.incident_number}</h2>
              <p className="text-sm text-slate-500">Detailed view and management</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="info">{incident.incident_type.replace(/_/g, ' ')}</Badge>
            <StatusBadge tone={toneForSeverity(incident.severity)}>{incident.severity}</StatusBadge>
            <StatusBadge tone={toneForStatus(incident.status)}>{incident.status}</StatusBadge>
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2">
          <div>
            <h3 className="font-medium text-slate-900 mb-3">Details</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between"><span className="text-slate-500">Incident Number</span><span className="font-mono font-medium text-slate-900">{incident.incident_number}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Type</span><span className="font-medium text-slate-900">{incident.incident_type.replace(/_/g, ' ')}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Severity</span><span><StatusBadge tone={toneForSeverity(incident.severity)}>{incident.severity}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Status</span><span><StatusBadge tone={toneForStatus(incident.status)}>{incident.status}</StatusBadge></span></div>
              <div className="flex justify-between"><span className="text-slate-500">Facility</span><span className="font-medium text-slate-900">{incident.facility_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Passport</span><span className="font-mono font-medium text-slate-900">{incident.passport_number || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Pickup Request</span><span className="font-medium text-slate-900">{incident.pickup_request_id ? `#${incident.pickup_request_id}` : '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Reported By</span><span className="font-medium text-slate-900">{incident.reported_by_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Assigned To</span><span className="font-medium text-slate-900">{incident.assigned_to_name || '—'}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Detected At</span><span className="font-medium text-slate-900">{formatDate(incident.detected_at)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Created At</span><span className="font-medium text-slate-900">{formatDate(incident.created_at)}</span></div>
              <div className="flex justify-between"><span className="text-slate-500">Updated At</span><span className="font-medium text-slate-900">{formatDate(incident.updated_at)}</span></div>
              {incident.acknowledged_at && (
                <div className="flex justify-between"><span className="text-slate-500">Acknowledged At</span><span className="font-medium text-slate-900">{formatDate(incident.acknowledged_at)}</span></div>
              )}
              {incident.resolved_at && (
                <div className="flex justify-between"><span className="text-slate-500">Resolved At</span><span className="font-medium text-slate-900">{formatDate(incident.resolved_at)}</span></div>
              )}
            </div>
          </div>

          <div>
            <h3 className="font-medium text-slate-900 mb-3">Title & Description</h3>
            {isEditing ? (
              <div className="space-y-3">
                <Input label="Title" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <textarea
                    value={editDescription}
                    onChange={(e) => setEditDescription(e.target.value)}
                    rows={4}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-500"
                  />
                </div>
                <div className="grid gap-3 md:grid-cols-2">
                  <Select label="Severity" value={editSeverity} onChange={(e) => setEditSeverity(e.target.value as any)}>
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </Select>
                  <Select label="Status" value={editStatus} onChange={(e) => setEditStatus(e.target.value as any)}>
                    <option value="OPEN">Open</option>
                    <option value="ACKNOWLEDGED">Acknowledged</option>
                    <option value="IN_PROGRESS">In Progress</option>
                    <option value="RESOLVED">Resolved</option>
                    <option value="CLOSED">Closed</option>
                  </Select>
                </div>
                <div className="flex gap-2">
                  <Button variant="secondary" onClick={() => { setIsEditing(false); if (incident) { setEditTitle(incident.title); setEditDescription(incident.description || ''); setEditSeverity(incident.severity as any); setEditStatus(incident.status as any); } }}>
                    Cancel
                  </Button>
                  <Button onClick={handleSave} disabled={saving}>
                    {saving ? 'Saving…' : 'Save Changes'}
                  </Button>
                </div>
              </div>
            ) : (
              <>
                <div className="mb-2 text-slate-700">{incident.title}</div>
                <div className="text-sm text-slate-600 whitespace-pre-wrap">{incident.description || 'No description provided.'}</div>
                <div className="mt-3 flex items-center gap-4 text-xs text-slate-500">
                  <span className="flex items-center gap-1"><AlertTriangle size={12} /> {incident.severity}</span>
                  <span className="flex items-center gap-1"><CheckCircle2 size={12} /> {incident.status}</span>
                </div>
                {showActions && (
                  <Button variant="ghost" size="sm" className="mt-3" onClick={() => setIsEditing(true)}>
                    <Edit2 size={14} className="mr-1" />
                    Edit Details
                  </Button>
                )}
              </>
            )}
          </div>
        </div>

        {incident.resolution_notes && (
          <div className="mt-6 pt-4 border-t border-slate-200">
            <h3 className="font-medium text-slate-900 mb-2">Resolution Notes</h3>
            <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-700 whitespace-pre-wrap">{incident.resolution_notes}</div>
          </div>
        )}

        {showActions && (
          <div className="mt-6 pt-4 border-t border-slate-200 space-y-4">
            <h3 className="font-medium text-slate-900 mb-3">Actions</h3>

            {actionError && (
              <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <AlertCircle size={16} className="inline mr-1" />
                {actionError}
              </div>
            )}

            {canAcknowledge && (
              <div className="flex items-center gap-3">
                <div className="flex-1">
                  <p className="font-medium text-slate-900">Acknowledge Incident</p>
                  <p className="text-sm text-slate-500">Mark as acknowledged and set acknowledgment timestamp.</p>
                </div>
                <Button onClick={handleAcknowledge} disabled={saving}>
                  {saving ? 'Acknowledging…' : 'Acknowledge'}
                </Button>
              </div>
            )}

            {canResolve && (
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-slate-900">Resolve Incident</p>
                    <p className="text-sm text-slate-500">Mark as resolved with resolution notes.</p>
                  </div>
                  <Button onClick={handleResolve} disabled={saving}>
                    {saving ? 'Resolving…' : 'Resolve'}
                  </Button>
                </div>
                <textarea
                  value={resolutionNotes}
                  onChange={(e) => setResolutionNotes(e.target.value)}
                  rows={3}
                  placeholder="Resolution notes (required for resolve/close)"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-500"
                />
              </div>
            )}

            {canClose && (
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-slate-900">Close Incident</p>
                  <p className="text-sm text-slate-500">Finalize and close the incident (requires resolution).</p>
                </div>
                <Button variant="secondary" onClick={handleClose} disabled={saving}>
                  {saving ? 'Closing…' : 'Close Incident'}
                </Button>
              </div>
            )}

            {incident.status === 'CLOSED' && (
              <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-center text-emerald-700">
                <CheckCircle2 size={24} className="mx-auto mb-2" />
                <div className="font-semibold">INCIDENT CLOSED</div>
                <div className="text-sm mt-1">This incident has been closed and no further actions are available.</div>
              </div>
            )}
          </div>
        )}
      </Card>
    </div>
  );
}