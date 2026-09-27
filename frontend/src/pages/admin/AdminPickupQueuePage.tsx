import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { Search, Filter, ChevronDown, ChevronUp, RotateCcw, UserPlus, Truck } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api } from '../../services/api';

function toneForStatus(status: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const st = status.toUpperCase();
  if (st === 'COLLECTED' || st === 'COMPLETED') return 'success';
  if (st === 'CANCELLED') return 'danger';
  if (st === 'IN_PROGRESS' || st === 'ACCEPTED') return 'info';
  if (st === 'ASSIGNED' || st === 'QUEUED' || st === 'REQUESTED') return 'warning';
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

export function AdminPickupQueuePage() {
  const { token, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [pickups, setPickups] = useState<Array<{ id: number; passport_id: number; passport_number: string; facility_id: number; facility_name: string | null; ward_id: number | null; ward_name: string | null; requested_by_user_id: number; assigned_collector_id: number | null; assigned_collector_name: string | null; priority: string; risk_score_snapshot: number | null; status: string; requested_at: string; assigned_at: string | null; accepted_at: string | null; pickup_started_at: string | null; completed_at: string | null; due_at: string | null; notes: string | null; waiting_minutes: number; waiting_hours: number; is_overdue: boolean; created_at: string; updated_at: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [collectors, setCollectors] = useState<Array<{ id: number; user_id: number; facility_id: number; employee_code: string; vehicle_number: string | null; phone: string | null; availability_status: string; active: boolean; user: { id: number; name: string; email: string } }>>([]);

  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [priorityFilter, setPriorityFilter] = useState(searchParams.get('priority') || '');
  const [unassignedOnly, setUnassignedOnly] = useState(searchParams.get('unassigned') === 'true');

  const [assignModalOpen, setAssignModalOpen] = useState(false);
  const [assignPickupId, setAssignPickupId] = useState<number | null>(null);
  const [assignCollectorId, setAssignCollectorId] = useState<string>('');
  const [assigning, setAssigning] = useState(false);
  const [assignError, setAssignError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    const params: Record<string, string | number | undefined> = {};
    if (search.trim()) params.search = search.trim();
    if (statusFilter) params.status = statusFilter;
    if (priorityFilter) params.priority = priorityFilter;
    if (unassignedOnly) params.collector = 0;

    setLoading(true);
    api.getPickupRequests(token, params)
      .then((data) => {
        if (active) {
          setPickups(data);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) setError(err instanceof Error ? err.message : 'Unable to load pickup queue.');
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [token, search, statusFilter, priorityFilter, unassignedOnly]);

  useEffect(() => {
    if (!token) return;
    api.getCollectors(token)
      .then((data) => {
        setCollectors(data.filter(c => c.active && c.availability_status === 'AVAILABLE'));
      })
      .catch(() => {});
  }, [token]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchParams({ search: search.trim() || undefined, status: statusFilter || undefined, priority: priorityFilter || undefined, unassigned: unassignedOnly || undefined }, { replace: true });
  };

  const handleOpenAssign = (pickupId: number) => {
    setAssignPickupId(pickupId);
    setAssignCollectorId('');
    setAssignError(null);
    setAssignModalOpen(true);
  };

  const handleAssign = async () => {
    if (!token || !assignPickupId || !assignCollectorId) return;
    setAssigning(true);
    setAssignError(null);
    try {
      await api.assignCollector(token, assignPickupId, Number(assignCollectorId));
      setAssignModalOpen(false);
      setAssignPickupId(null);
      window.location.reload();
    } catch (err) {
      setAssignError(err instanceof Error ? err.message : 'Failed to assign collector.');
    } finally {
      setAssigning(false);
    }
  };

  const hasFilters = search.trim() || statusFilter || priorityFilter || unassignedOnly;

  const openCount = useMemo(() => pickups.filter((p) => !['COLLECTED', 'CANCELLED'].includes(p.status)).length, [pickups]);

  if (!token || !user || !['ADMIN', 'REGULATOR'].includes(user.role)) {
    return (
      <div className="max-w-7xl mx-auto space-y-6 py-8 px-4">
        <Card>
          <div className="text-center text-slate-600 py-4">Admin or Regulator access required.</div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Pickup operations</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Pickup Queue</h1>
      </div>

      <Card>
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <Truck size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Pickup queue</h2>
              <p className="text-sm text-slate-500">All pickup requests across facilities</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={openCount > 0 ? 'warning' : 'success'}>{openCount} active</Badge>
            <Button variant="secondary" size="sm" onClick={() => { setSearchParams({}, { replace: true }); window.location.reload(); }}>
              <RotateCcw size={14} className="mr-1" />
              Refresh
            </Button>
          </div>
        </div>

        <form onSubmit={handleSearchSubmit} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              label="Search by passport"
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="e.g., TRV-20260926-..."
            />
            <Select label="Status" value={statusFilter} onChange={(e) => handleStatusChange(e.target.value)}>
              <option value="">All statuses</option>
              <option value="REQUESTED">Requested</option>
              <option value="QUEUED">Queued</option>
              <option value="ASSIGNED">Assigned</option>
              <option value="ACCEPTED">Accepted</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="COLLECTED">Collected</option>
              <option value="CANCELLED">Cancelled</option>
            </Select>
            <Select label="Priority" value={priorityFilter} onChange={(e) => handlePriorityChange(e.target.value)}>
              <option value="">All priorities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </Select>
            <label className="flex items-center gap-2">
              <input type="checkbox" checked={unassignedOnly} onChange={(e) => setUnassignedOnly(e.target.checked)} className="rounded border-slate-300 text-slate-900 focus:ring-slate-500" />
              <span className="text-sm text-slate-700">Unassigned only</span>
            </label>
          </div>
          <div className="flex items-center gap-3">
            <Button type="submit">
              <Search size={14} className="mr-1" />
              Search
            </Button>
            {hasFilters && (
              <Button type="button" variant="ghost" size="sm" onClick={() => { setSearch(''); setStatusFilter(''); setPriorityFilter(''); setUnassignedOnly(false); setSearchParams({}, { replace: true }); }}>
                Clear filters
              </Button>
            )}
          </div>
        </form>

        {loading && <div className="text-center text-slate-500 py-8">Loading pickup queue…</div>}
        {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <>
            <Table
              headers={['Passport', 'Ward', 'Priority', 'Risk', 'Waiting', 'Due', 'Status', 'Collector', 'Actions']}
              rows={pickups.map((pickup) => [
                <Link to={`/ward/passports/${pickup.passport_id}`} className="font-mono text-slate-900 hover:underline">{pickup.passport_number}</Link>,
                pickup.ward_name || '—',
                <StatusBadge key={pickup.id} tone={priorityTone(pickup.priority)}>{pickup.priority}</StatusBadge>,
                pickup.risk_score_snapshot !== null ? pickup.risk_score_snapshot.toFixed(1) : '—',
                pickup.waiting_minutes ? `${pickup.waiting_minutes} min` : '—',
                pickup.due_at ? formatDate(pickup.due_at) : '—',
                <StatusBadge tone={toneForStatus(pickup.status)}>{pickup.status}</StatusBadge>,
                pickup.assigned_collector_name ? (
                  <span className="flex items-center gap-1 text-slate-700">
                    <UserPlus size={12} className="text-emerald-600" />
                    {pickup.assigned_collector_name}
                  </span>
                ) : (
                  <span className="text-slate-400 italic">Unassigned</span>
                ),
                pickup.assigned_collector_id ? (
                  <span className="text-slate-400 text-sm">Assigned</span>
                ) : (
                  <Button variant="secondary" size="sm" onClick={() => handleOpenAssign(pickup.id)}>
                    <UserPlus size={14} className="mr-1" />
                    Assign
                  </Button>
                ),
              ])}
            />

            {!loading && pickups.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                <Truck size={32} className="mx-auto mb-2 opacity-40" />
                <p>No pickup requests found.</p>
                {hasFilters && <p className="text-sm mt-1">Try adjusting your filters.</p>}
              </div>
            )}
          </>
        )}

        {assignModalOpen && assignPickupId !== null && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <div className="bg-white rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
              <h3 className="text-lg font-semibold text-slate-900 mb-4">Assign Collector</h3>
              {assignError && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 mb-4">{assignError}</div>}
              <Select label="Collector" value={assignCollectorId} onChange={(e) => setAssignCollectorId(e.target.value)}>
                <option value="">Select a collector</option>
                {collectors.map((c) => (
                  <option key={c.id} value={String(c.id)}>{c.user.name} ({c.employee_code}) - {c.availability_status}</option>
                ))}
              </Select>
              <div className="mt-4 flex gap-2">
                <Button variant="secondary" className="flex-1" onClick={() => setAssignModalOpen(false)} disabled={assigning}>Cancel</Button>
                <Button className="flex-1" onClick={handleAssign} disabled={assigning || !assignCollectorId}>
                  {assigning ? 'Assigning...' : 'Assign Collector'}
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}