import { useState, useEffect } from 'react';
import { FileText, Plus } from 'lucide-react';
import { Link } from 'react-router-dom';

import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { Card } from '../../components/ui/Card';
import { StatusBadge } from '../../components/ui/StatusBadge';
import { Table } from '../../components/ui/Table';
import { useAuth } from '../../contexts/AuthContext';
import { api, type WastePassport } from '../../services/api';

function statusTone(status: string) {
  const value = String(status || '').toUpperCase();
  if (value.includes('REJECTED') || value.includes('CRITICAL')) return 'danger';
  if (value.includes('READY') || value.includes('PICKUP') || value.includes('CLASSIFIED')) return 'warning';
  if (value === 'COMPLETED' || value === 'VERIFIED') return 'success';
  return 'neutral';
}

function priorityTone(priority: string): 'success' | 'warning' | 'danger' | 'neutral' | 'info' {
  const p = priority.toUpperCase();
  if (p === 'CRITICAL') return 'danger';
  if (p === 'HIGH') return 'warning';
  if (p === 'MEDIUM') return 'info';
  return 'success';
}

export function WardPassportsPage() {
  const { token } = useAuth();
  const [passports, setPassports] = useState<WastePassport[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let active = true;
    api.getPassports(token)
      .then((rows) => {
        if (active) {
          setPassports(rows);
          setError(null);
        }
      })
      .catch((err) => {
        if (active) {
          setError(err instanceof Error ? err.message : 'Unable to load passports.');
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });

    return () => {
      active = false;
    };
  }, [token]);

  return (
    <div className="space-y-6 min-h-0 w-full">
      <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.2em] text-slate-500">Waste traceability</p>
          <h1 className="mt-1 text-3xl font-semibold text-slate-900">Waste Passports</h1>
        </div>
        <Link to="/ward/passports/new">
          <Button>
            <Plus className="mr-2" size={16} />
            New Passport
          </Button>
        </Link>
      </div>

      <Card>
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-slate-100 p-2 text-slate-700">
              <FileText size={18} />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-slate-900">Passport registry</h2>
              <p className="text-sm text-slate-500">Operational index for digital waste records</p>
            </div>
          </div>
          <Badge variant="info">{passports.filter((item) => !['COMPLETED', 'REJECTED'].includes(String(item.status).toUpperCase())).length} active</Badge>
        </div>

        {loading && <div className="text-sm text-slate-500">Loading passports...</div>}
        {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

        {!loading && !error && (
          <Table
            headers={['Passport ID', 'Ward', 'Risk', 'Status', 'Updated', 'Actions']}
            rows={passports.map((passport) => [
              <Link to={`/ward/passports/${passport.id}`} className="font-mono text-slate-900 hover:underline">{passport.passport_number}</Link>,
              passport.ward_name || '—',
              <StatusBadge key={passport.id} tone={priorityTone(passport.risk_priority || 'LOW')}>{passport.risk_priority || 'LOW'}</StatusBadge>,
              <StatusBadge tone={statusTone(passport.status)}>{passport.status}</StatusBadge>,
              passport.updated_at ? new Date(passport.updated_at).toLocaleString() : '—',
              <Link to={`/ward/passports/${passport.id}`}>
                <Button variant="ghost" size="sm" aria-label={`View ${passport.passport_number}`}>
                  View
                </Button>
              </Link>,
            ])}
          />
        )}
      </Card>
    </div>
  );
}
