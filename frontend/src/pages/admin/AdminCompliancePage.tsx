import { useEffect, useState, useMemo } from 'react';
import { Search, Filter, ChevronLeft, ChevronRight, Calendar, Download, TrendingUp, TrendingDown, Minus } from 'lucide-react';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { Input } from '../../components/ui/Input';
import { Select } from '../../components/ui/Select';
import { MetricCard } from '../../components/ui/MetricCard';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api, type DashboardSummaryResponse, type TraceabilityReport, type FacilityReport, type RiskReport, type PickupReport, type TreatmentReport } from '../../services/api';

function toneForRate(rate: number): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  if (rate >= 90) return 'success';
  if (rate >= 70) return 'warning';
  return 'danger';
}

function formatNumber(num: number): string {
  return new Intl.NumberFormat().format(num);
}

function formatPercent(num: number): string {
  return `${num.toFixed(1)}%`;
}

export function AdminCompliancePage() {
  const { token, user } = useAuth();
  const [dashboard, setDashboard] = useState<DashboardSummaryResponse | null>(null);
  const [traceability, setTraceability] = useState<TraceabilityReport | null>(null);
  const [facilityReport, setFacilityReport] = useState<FacilityReport>([]);
  const [riskReport, setRiskReport] = useState<RiskReport | null>(null);
  const [pickupReport, setPickupReport] = useState<PickupReport | null>(null);
  const [treatmentReport, setTreatmentReport] = useState<TreatmentReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dateRange, setDateRange] = useState<'today' | 'last_7_days' | 'last_30_days'>('last_30_days');
  const [selectedFacility, setSelectedFacility] = useState<string>('');

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);

    const fetchAll = async () => {
      try {
        const [dash, trace, facilities, risk, pickups, treatment] = await Promise.all([
          api.getDashboardSummary(token),
          api.getTraceabilityReport(token),
          api.getFacilityReport(token),
          api.getRiskReport(token, { range: dateRange }),
          api.getPickupReport(token, { range: dateRange }),
          api.getTreatmentReport(token),
        ]);
        if (active) {
          setDashboard(dash);
          setTraceability(trace);
          setFacilityReport(facilities);
          setRiskReport(risk);
          setPickupReport(pickups);
          setTreatmentReport(treatment);
          setError(null);
        }
      } catch (err) {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load compliance data.');
        }
      } finally {
        if (active) setLoading(false);
      }
    };

    fetchAll();
    return () => { active = false; };
  }, [token, dateRange]);

  const overviewMetrics = useMemo(() => {
    if (!dashboard) return [];
    const ps = dashboard.passport_summary;
    const pk = dashboard.pickup_summary;
    const tr = dashboard.treatment_summary;
    const inc = dashboard.incident_summary;

    const pickupCompletionRate = pk.total_requests > 0 ? ((pk.completed / pk.total_requests) * 100) : 0;
    const treatmentVerificationRate = tr.received_count > 0 ? ((tr.verified / tr.received_count) * 100) : 0;
    const traceabilityRate = traceability?.completion_rate ?? 0;

    return [
      { label: 'Total Passports', value: formatNumber(ps.total), change: `${ps.active} active`, tone: 'default' as const, icon: <TrendingUp size={16} /> },
      { label: 'Completed Passports', value: formatNumber(ps.completed), change: formatPercent((ps.total > 0 ? (ps.completed / ps.total) * 100 : 0)), tone: 'success' as const, icon: <TrendingUp size={16} /> },
      { label: 'Overdue Pickups', value: formatNumber(pk.overdue), change: `${pk.pending} pending`, tone: pk.overdue > 0 ? 'danger' as const : 'success' as const, icon: <TrendingDown size={16} /> },
      { label: 'Open Incidents', value: formatNumber(inc.open), change: `${inc.total} total`, tone: inc.open > 0 ? 'warning' as const : 'success' as const, icon: <TrendingUp size={16} /> },
      { label: 'Pickup Completion', value: formatPercent(pickupCompletionRate), change: `${pk.completed}/${pk.total_requests}`, tone: toneForRate(pickupCompletionRate), icon: <TrendingUp size={16} /> },
      { label: 'Treatment Verified', value: formatPercent(treatmentVerificationRate), change: `${tr.verified}/${tr.received_count}`, tone: toneForRate(treatmentVerificationRate), icon: <TrendingUp size={16} /> },
      { label: 'Traceability Rate', value: formatPercent(traceabilityRate), change: `${traceability?.total_passports ?? 0} passports`, tone: toneForRate(traceabilityRate), icon: <TrendingUp size={16} /> },
      { label: 'Verification Pending', value: formatNumber(tr.verification_pending), change: `${tr.treatment_pending} in treatment`, tone: tr.verification_pending > 0 ? 'info' as const : 'success' as const, icon: <TrendingUp size={16} /> },
    ];
  }, [dashboard, traceability, pickupReport]);

  const traceabilityStages = useMemo(() => {
    if (!traceability) return [];
    const order = [
      'Created', 'Classified', 'QR Generated', 'Pickup Requested',
      'Collected', 'Transported', 'Received', 'Treatment Completed',
      'Verified', 'Closed'
    ];
    return order.map((stage) => ({
      stage,
      count: traceability.stages[stage] ?? 0,
    }));
  }, [traceability]);

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
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Compliance & Analytics</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">Operational Compliance</h1>
        </div>
        <div className="flex items-center gap-3">
          <Select label="Date Range" value={dateRange} onChange={(e) => setDateRange(e.target.value as any)}>
            <option value="today">Today</option>
            <option value="last_7_days">Last 7 Days</option>
            <option value="last_30_days">Last 30 Days</option>
          </Select>
          <Select label="Facility" value={selectedFacility} onChange={(e) => setSelectedFacility(e.target.value)}>
            <option value="">All Facilities</option>
            {facilityReport.map((f) => (
              <option key={f.facility_id} value={String(f.facility_id)}>{f.facility_name}</option>
            ))}
          </Select>
          <Button variant="secondary" size="sm" onClick={() => { window.location.reload(); }}>
            <Search size={14} className="mr-1" />
            Refresh
          </Button>
        </div>
      </div>

      {loading && <div className="rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">Loading compliance data…</div>}
      {error && <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700">{error}</div>}

      {!loading && !error && (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-8">
            {overviewMetrics.map((metric) => (
              <MetricCard key={metric.label} {...metric} />
            ))}
          </div>

          <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
            <Card>
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold text-slate-900">Traceability Lifecycle</h2>
                  <p className="text-sm text-slate-500">Passport progression through waste management stages</p>
                </div>
                {traceability && (
                  <Badge variant={toneForRate(traceability.completion_rate)}>{formatPercent(traceability.completion_rate)} complete</Badge>
                )}
              </div>

              <div className="space-y-3">
                {traceabilityStages.map(({ stage, count }, idx) => {
                  const isLast = idx === traceabilityStages.length - 1;
                  const prevCount = idx > 0 ? traceabilityStages[idx - 1].count : 0;
                  const drop = prevCount > 0 ? Math.round(((prevCount - count) / prevCount) * 100) : 0;
                  return (
                    <div key={stage} className="flex items-center gap-4">
                      <div className="w-10 text-right text-sm text-slate-500">{idx + 1}.</div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-slate-900 truncate">{stage}</span>
                          <span className="font-mono text-slate-700">{formatNumber(count)}</span>
                        </div>
                        <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden mt-1">
                          <div
                            className={`h-2 rounded-full transition-all ${
                              count > 0 ? (drop > 20 ? 'bg-rose-500' : drop > 10 ? 'bg-amber-500' : 'bg-emerald-500') : 'bg-slate-200'
                            }`}
                            style={{ width: prevCount > 0 ? `${Math.max(0, 100 - drop)}%` : '0%' }}
                          />
                        </div>
                      </div>
                      <div className="w-16 text-right text-xs text-slate-500">
                        {prevCount > 0 && drop > 0 ? <span className="flex items-center gap-1 text-rose-600"><TrendingDown size={10} /> {drop}% drop</span> : <Minus size={10} className="mx-auto text-slate-400" />}
                      </div>
                    </div>
                  );
                })}
              </div>
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Facility Overview</h2>
              {facilityReport.length > 0 ? (
                <Table
                  headers={['Facility', 'Passports', 'Waste (kg)', 'Incidents', 'Traceability']}
                  rows={facilityReport.map((f) => [
                    <span className="font-medium text-slate-900">{f.facility_name}</span>,
                    formatNumber(f.passport_volume),
                    formatNumber(f.waste_weight_kg),
                    formatNumber(f.incident_count),
                    <span className={`font-mono ${toneForRate(f.traceability_completion_rate) === 'success' ? 'text-emerald-600' : toneForRate(f.traceability_completion_rate) === 'warning' ? 'text-amber-600' : 'text-rose-600'}`}>{formatPercent(f.traceability_completion_rate)}</span>,
                  ])}
                />
              ) : (
                <div className="text-center text-slate-500 py-8">No facility data available.</div>
              )}
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Pickup Performance</h2>
              {pickupReport && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-4">
                    <MetricCard label="Total Requests" value={formatNumber(pickupReport.total_requests)} change="in range" tone="default" icon={<Search size={16} />} />
                    <MetricCard label="Completed" value={formatNumber(pickupReport.completed)} change={`${pickupReport.pending} pending`} tone="success" icon={<TrendingUp size={16} />} />
                    <MetricCard label="Overdue" value={formatNumber(pickupReport.overdue)} change={`${pickupReport.average_waiting_time_minutes.toFixed(0)} min avg wait`} tone={pickupReport.overdue > 0 ? 'danger' : 'success'} icon={<TrendingDown size={16} />} />
                    <MetricCard label="Avg Response" value={`${pickupReport.average_response_time_minutes.toFixed(1)} min`} change="response time" tone="info" icon={<Calendar size={16} />} />
                  </div>
                  <div className="grid gap-2">
                    {Object.entries(pickupReport.priority_distribution).map(([priority, count]) => (
                      <div key={priority} className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                          <StatusBadge tone={priority === 'CRITICAL' ? 'danger' : priority === 'HIGH' ? 'warning' : priority === 'MEDIUM' ? 'info' : 'success'}>{priority}</StatusBadge>
                          <span className="font-medium text-slate-900">{priority}</span>
                        </span>
                        <span className="font-mono text-slate-700">{formatNumber(count)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Treatment Verification</h2>
              {treatmentReport && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-4">
                    <MetricCard label="Received" value={formatNumber(treatmentReport.received_count)} change="" tone="default" icon={<TrendingUp size={16} />} />
                    <MetricCard label="Verified" value={formatNumber(treatmentReport.verified)} change={formatPercent(treatmentReport.received_count > 0 ? (treatmentReport.verified / treatmentReport.received_count) * 100 : 0)} tone="success" icon={<TrendingUp size={16} />} />
                    <MetricCard label="Pending" value={formatNumber(treatmentReport.verification_pending)} change={`${treatmentReport.treatment_pending} in treatment`} tone="info" icon={<TrendingUp size={16} />} />
                    <MetricCard label="Avg Hours" value={`${treatmentReport.average_treatment_completion_hours.toFixed(1)}h`} change="per treatment" tone="info" icon={<Calendar size={16} />} />
                  </div>
                  <div className="grid gap-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-900">Rejected</span>
                      <span className="font-mono text-rose-600">{formatNumber(treatmentReport.rejected)}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-slate-900">Treatment Completed</span>
                      <span className="font-mono text-emerald-600">{formatNumber(treatmentReport.treatment_completed)}</span>
                    </div>
                  </div>
                </div>
              )}
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Incident Overview</h2>
              {dashboard && (
                <div className="space-y-4">
                  <div className="grid gap-4 md:grid-cols-3">
                    <MetricCard label="Total" value={formatNumber(dashboard.incident_summary.total)} change="" tone="default" icon={<Search size={16} />} />
                    <MetricCard label="Open" value={formatNumber(dashboard.incident_summary.open)} change="" tone={dashboard.incident_summary.open > 0 ? 'warning' : 'success'} icon={<TrendingUp size={16} />} />
                    <MetricCard label="Resolved" value={formatNumber(dashboard.incident_summary.resolved)} change="" tone="success" icon={<TrendingUp size={16} />} />
                  </div>
                  {riskReport && (
                    <div className="grid gap-2">
                      {Object.entries(riskReport.distribution).map(([level, pct]) => (
                        <div key={level} className="flex items-center justify-between text-sm">
                          <span className="flex items-center gap-2">
                            <StatusBadge tone={level === 'CRITICAL' ? 'danger' : level === 'HIGH' ? 'warning' : level === 'MEDIUM' ? 'info' : 'success'}>{level}</StatusBadge>
                            <span className="font-medium text-slate-900">{level}</span>
                          </span>
                          <span className="font-mono text-slate-700">{formatPercent(pct)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">Risk Distribution</h2>
              {dashboard && (
                <div className="space-y-4">
                  <div className="grid gap-2">
                    {Object.entries(dashboard.risk_summary.distribution).map(([level, pct]) => (
                      <div key={level} className="flex items-center justify-between text-sm">
                        <span className="flex items-center gap-2">
                          <StatusBadge tone={level === 'CRITICAL' ? 'danger' : level === 'HIGH' ? 'warning' : level === 'MEDIUM' ? 'info' : 'success'}>{level}</StatusBadge>
                          <span className="font-medium text-slate-900">{level}</span>
                        </span>
                        <span className="font-mono text-slate-700">{formatPercent(pct)}</span>
                      </div>
                    ))}
                  </div>
                  <div className="pt-4 border-t border-slate-200">
                    <p className="text-sm text-slate-500">Passports by risk priority. Distribution shows relative share of each level.</p>
                  </div>
                </div>
              )}
            </Card>

          </div>
        </>
      )}
    </div>
  );
}