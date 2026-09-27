import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { AlertTriangle, Search, Filter, ChevronDown, ChevronUp, RotateCcw, Eye } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api, type Incident, type IncidentListResponse } from '../../services/api';

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

export function AdminIncidentsPage() {
  const { token, user } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [limit] = useState(20);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState(searchParams.get('search') || '');
  const [severityFilter, setSeverityFilter] = useState(searchParams.get('severity') || '');
  const [statusFilter, setStatusFilter] = useState(searchParams.get('status') || '');
  const [facilityFilter, setFacilityFilter] = useState(searchParams.get('facility') || '');

  const [showFilters, setShowFilters] = useState(false);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    const params: Record<string, string | number | undefined> = {
      page,
      limit,
    };
    if (search.trim()) params.incident_number = search.trim();
    if (severityFilter) params.severity = severityFilter;
    if (statusFilter) params.status = statusFilter;
    if (facilityFilter) params.facility = Number(facilityFilter);

    setLoading(true);
    api.getIncidents(token, params)
      .then((data) => {
        if (active) {
          setIncidents(data.items);
          setTotal(data.total);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load incidents.');
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });

    return () => { active = false; };
  }, [token, page, search, severityFilter, statusFilter, facilityFilter]);

  const handleSearchChange = (value: string) => {
    setSearch(value);
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setSearchParams({ search: search.trim() || undefined, severity: severityFilter || undefined, status: statusFilter || undefined, facility: facilityFilter || undefined }, { replace: true });
  };

  const handleSeverityChange = (value: string) => {
    setSeverityFilter(value);
    setPage(1);
  };

  const handleStatusChange = (value: string) => {
    setStatusFilter(value);
    setPage(1);
  };

  const handleFacilityChange = (value: string) => {
    setFacilityFilter(value);
    setPage(1);
  };

  const handleClearFilters = () => {
    setSearch('');
    setSeverityFilter('');
    setStatusFilter('');
    setFacilityFilter('');
    setPage(1);
    setSearchParams({}, { replace: true });
  };

  const hasFilters = search.trim() || severityFilter || statusFilter || facilityFilter;

  const openCount = useMemo(() => incidents.filter((i) => i.status === 'OPEN').length, [incidents]);

  if (!token || !user || !['ADMIN', 'REGULATOR'].includes(user.role)) {
    return (
      <div className="max-w-4xl mx-auto space-y-6 py-8 px-4">
        <Card>
          <div className="text-center text-slate-600 py-4">Admin or Regulator access required.</div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Safety intelligence</p>
        <h1 className="mt-1 text-3xl font-semibold text-slate-900">Incidents & Compliance</h1>
      </div>

      <Card>
        <div className="mb-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <AlertTriangle size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Incident registry</h2>
              <p className="text-sm text-slate-500">Tracking exceptions and escalations</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Badge variant={openCount > 0 ? 'warning' : 'success'}>{openCount} open</Badge>
            <Button variant="secondary" size="sm" onClick={() => { setPage(1); window.location.reload(); }}>
              <RotateCcw size={14} className="mr-1" />
              Refresh
            </Button>
          </div>
        </div>

        <form onSubmit={handleSearchSubmit} className="space-y-4">
          <div className="flex flex-col sm:flex-row gap-3">
            <Input
              label="Search by incident number"
              type="text"
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="e.g., INC-0042"
            />
            <Select label="Severity" value={severityFilter} onChange={(e) => handleSeverityChange(e.target.value)}>
              <option value="">All severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </Select>
            <Select label="Status" value={statusFilter} onChange={(e) => handleStatusChange(e.target.value)}>
              <option value="">All statuses</option>
              <option value="OPEN">Open</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="IN_PROGRESS">In Progress</option>
              <option value="RESOLVED">Resolved</option>
              <option value="CLOSED">Closed</option>
            </Select>
            <Select label="Facility" value={facilityFilter} onChange={(e) => handleFacilityChange(e.target.value)}>
              <option value="">All facilities</option>
              <option value="1">City General Hospital</option>
              <option value="2">Metro Medical Center</option>
              <option value="3">Rural Health Clinic</option>
              <option value="4">Central Treatment Facility</option>
            </Select>
          </div>
          <div className="flex items-center gap-3">
            <Button type="submit">
              <Search size={14} className="mr-1" />
              Search
            </Button>
            {hasFilters && (
              <Button type="button" variant="ghost" size="sm" onClick={handleClearFilters}>
                Clear filters
              </Button>
            )}
          </div>
        </form>

        {loading && <div className="text-center text-slate-500 py-8">Loading incidents…</div>}
        {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <>
            <Table
              headers={['Incident', 'Type', 'Severity', 'Facility', 'Passport', 'Status', 'Created', 'Actions']}
              rows={incidents.map((incident) => [
                <Link to={`/admin/incidents/${incident.id}`} className="font-mono text-slate-900 hover:underline">{incident.incident_number}</Link>,
                incident.incident_type.replace(/_/g, ' '),
                <StatusBadge tone={toneForSeverity(incident.severity)}>{incident.severity}</StatusBadge>,
                incident.facility_name || '—',
                incident.passport_number || '—',
                <StatusBadge tone={toneForStatus(incident.status)}>{incident.status}</StatusBadge>,
                incident.created_at ? new Date(incident.created_at).toLocaleString() : '—',
                <Link to={`/admin/incidents/${incident.id}`}>
                  <Button variant="ghost" size="sm" aria-label={`View ${incident.incident_number}`}>
                    <Eye size={14} />
                  </Button>
                </Link>,
              ])}
            />

            {!loading && incidents.length === 0 && (
              <div className="text-center text-slate-500 py-8">
                <AlertTriangle size={32} className="mx-auto mb-2 opacity-40" />
                <p>No incidents found.</p>
                {hasFilters && <p className="text-sm mt-1">Try adjusting your filters.</p>}
              </div>
            )}

            {total > limit && (
              <div className="mt-4 flex items-center justify-between text-sm text-slate-500">
                <span>Showing {((page - 1) * limit) + 1}–{Math.min(page * limit, total)} of {total} incidents</span>
                <div className="flex gap-2">
                  <Button variant="secondary" size="sm" onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}>
                    <ChevronUp size={14} />
                  </Button>
                  <Button variant="secondary" size="sm" onClick={() => setPage((p) => p + 1)} disabled={page * limit >= total}>
                    <ChevronDown size={14} />
                  </Button>
                </div>
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  );
}