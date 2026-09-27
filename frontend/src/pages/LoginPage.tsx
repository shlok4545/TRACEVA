import { Activity, Eye, EyeOff, ShieldCheck } from 'lucide-react';
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { Badge } from '../components/ui/Badge';
import { Button } from '../components/ui/Button';
import { Card } from '../components/ui/Card';
import { Input } from '../components/ui/Input';
import { useAuth } from '../contexts/AuthContext';
import { defaultDashboardByRole } from '../config/navigation';

type LoginPageProps = {
  backendStatus: 'Connected' | 'Disconnected';
};

export function LoginPage({ backendStatus }: LoginPageProps) {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState('admin@traceva.demo');
  const [password, setPassword] = useState('Traceva@2026');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError('');

    if (!email.trim() || !password.trim()) {
      setError('Email and password are required.');
      return;
    }

    try {
      setIsSubmitting(true);
      const user = await login(email.trim(), password);
      navigate(defaultDashboardByRole[user.role] ?? '/dashboard', { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message.replace(/"/g, '') : 'Unable to sign in. Please check your credentials.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 px-4 py-10">
      <div className="grid w-full max-w-6xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-soft lg:grid-cols-2">
        <div className="bg-slate-950 p-8 text-slate-50 lg:px-10 lg:py-12">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-500/20 text-lg font-semibold text-emerald-300">T</div>
            <div>
              <div className="text-2xl font-semibold">TRACEVA</div>
              <div className="text-sm text-slate-400">Track. Verify. Protect.</div>
            </div>
          </div>

          <div className="mt-12 space-y-4">
            <Badge variant="success">System Ready</Badge>
            <h1 className="text-3xl font-semibold leading-tight">Smart healthcare waste operations, built for compliance and traceability.</h1>
            <p className="max-w-md text-sm leading-6 text-slate-300">
              Secure digital waste passports, pickup coordination, and treatment verification for hospital operations.
            </p>
          </div>

          <div className="mt-10 flex items-center gap-4 rounded-xl border border-slate-800 bg-slate-900/50 p-4">
            <div className="rounded-lg bg-emerald-500/20 p-2 text-emerald-300">
              <ShieldCheck size={18} />
            </div>
            <div>
              <div className="text-sm font-medium">Backend status</div>
              <div className="text-sm text-slate-300">{backendStatus}</div>
            </div>
          </div>
        </div>

        <div className="p-8 lg:p-10">
          <div className="mb-6 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-slate-500">Medical waste operations</div>
              <h2 className="text-2xl font-semibold text-slate-900">Sign in</h2>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-700">
              <Activity size={12} />
              Local dev
            </div>
          </div>

          <Card className="p-6">
            <form className="space-y-4" onSubmit={handleSubmit}>
              <Input label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" />
              <div className="relative">
                <Input
                  label="Password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  autoComplete="current-password"
                  className="pr-10"
                />
                <button type="button" onClick={() => setShowPassword((value) => !value)} className="absolute bottom-3 right-3 text-slate-500" aria-label="Show or hide password">
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>

              {error && <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">{error}</div>}

              <Button className="w-full" type="submit" disabled={isSubmitting}>
                {isSubmitting ? 'Signing in...' : 'Continue to dashboard'}
              </Button>
            </form>
          </Card>

          <div className="mt-6 rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
            Demo credentials are documented in the README for local development: admin@traceva.demo / Traceva@2026
          </div>
        </div>
      </div>
    </div>
  );
}
