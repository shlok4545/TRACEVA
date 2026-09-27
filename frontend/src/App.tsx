import { useState } from 'react';
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom';

import { MobileNav } from './components/layout/MobileNav';
import { Sidebar } from './components/layout/Sidebar';
import { Topbar } from './components/layout/Topbar';
import { ErrorState } from './components/ui/ErrorState';
import { LoadingState } from './components/ui/LoadingState';
import { defaultDashboardByRole, roleNavigation } from './config/navigation';
import { useAuth } from './contexts/AuthContext';
import { useApiHealth } from './hooks/useApiHealth';
import { LoginPage } from './pages/LoginPage';
import { NotificationsPage } from './pages/NotificationsPage';
import { AdminCompliancePage } from './pages/admin/AdminCompliancePage';
import { AdminIncidentsPage } from './pages/admin/AdminIncidentsPage';
import { AdminIncidentDetailPage } from './pages/admin/AdminIncidentDetailPage';
import { AdminPickupQueuePage } from './pages/admin/AdminPickupQueuePage';
import { CollectorAssignmentsPage } from './pages/collector/CollectorAssignmentsPage';
import { CollectorScanPage } from './pages/collector/CollectorScanPage';
import { FacilityReceivingPage } from './pages/facility/FacilityReceivingPage';
import { FacilityReceivingDetailPage } from './pages/facility/FacilityReceivingDetailPage';
import { FacilityTreatmentPage } from './pages/facility/FacilityTreatmentPage';
import { FacilityTreatmentDetailPage } from './pages/facility/FacilityTreatmentDetailPage';
import { DashboardPage } from './pages/DashboardPage';
import { WardPassportDetailPage } from './pages/ward/WardPassportDetailPage';
import { WardPassportNewPage } from './pages/ward/WardPassportNewPage';
import { WardPassportsPage } from './pages/ward/WardPassportsPage';
import { WardWasteEntryPage } from './pages/ward/WardWasteEntryPage';

function AppLayout({ children }: { children: React.ReactNode }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-100 text-slate-800">
      <Sidebar user={user} navItems={user ? roleNavigation[user.role] ?? [] : []} onLogout={logout} />
      <MobileNav open={mobileOpen} onClose={() => setMobileOpen(false)} user={user} navItems={user ? roleNavigation[user.role] ?? [] : []} onLogout={logout} />
      <div className="lg:ml-72">
        <Topbar onMenuClick={() => setMobileOpen(true)} user={user} onLogout={logout} />
        <main className="p-4 sm:p-6">{children}</main>
      </div>
    </div>
  );
}

function ProtectedRoute({ allowedRoles }: { allowedRoles?: string[] }) {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6"><LoadingState label="Loading session..." /></div>;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={defaultDashboardByRole[user.role] ?? '/dashboard'} replace />;
  }

  return <Outlet />;
}

function App() {
  const { status, loading, error } = useApiHealth();
  const { isAuthenticated, user, isLoading } = useAuth();

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6"><LoadingState label="Starting TRACEVA ..." /></div>;
  }

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-100 p-6">
        <div className="max-w-xl">
          <ErrorState message="The backend is unavailable. Please start the TRACEVA API server." />
        </div>
      </div>
    );
  }

  const defaultPath = user ? defaultDashboardByRole[user.role] || '/dashboard' : '/login';

  return (
    <Routes>
      <Route path="/login" element={isAuthenticated ? <Navigate to={defaultPath} replace /> : <LoginPage backendStatus={status} />} />
      <Route path="/" element={<Navigate to={defaultPath} replace />} />

      <Route element={<ProtectedRoute />}>
        <Route
          path="/dashboard"
          element={
            <AppLayout>
              <DashboardPage backendStatus={status} />
            </AppLayout>
          }
        />
        <Route
          path="/notifications"
          element={
            <AppLayout>
              <NotificationsPage />
            </AppLayout>
          }
        />
        <Route
          path="/ward/waste-entry"
          element={
            <AppLayout>
              <WardWasteEntryPage />
            </AppLayout>
          }
        />
        <Route
          path="/ward/passports"
          element={
            <AppLayout>
              <WardPassportsPage />
            </AppLayout>
          }
        />
        <Route
          path="/ward/passports/:passportId"
          element={
            <AppLayout>
              <WardPassportDetailPage />
            </AppLayout>
          }
        />
        <Route
          path="/ward/passports/new"
          element={
            <AppLayout>
              <WardPassportNewPage />
            </AppLayout>
          }
        />
        <Route
          path="/collector/assignments"
          element={
            <AppLayout>
              <CollectorAssignmentsPage />
            </AppLayout>
          }
        />
        <Route
          path="/collector/scan"
          element={
            <AppLayout>
              <CollectorScanPage />
            </AppLayout>
          }
        />
        <Route
          path="/facility/receiving"
          element={
            <AppLayout>
              <FacilityReceivingPage />
            </AppLayout>
          }
        />
        <Route
          path="/facility/receiving/:passportId"
          element={
            <AppLayout>
              <FacilityReceivingDetailPage />
            </AppLayout>
          }
        />
        <Route
          path="/facility/treatment"
          element={
            <AppLayout>
              <FacilityTreatmentPage />
            </AppLayout>
          }
        />
        <Route
          path="/facility/treatment/:recordId"
          element={
            <AppLayout>
              <FacilityTreatmentDetailPage />
            </AppLayout>
          }
        />
        <Route
          path="/admin/compliance"
          element={
            <AppLayout>
              <AdminCompliancePage />
            </AppLayout>
          }
        />
        <Route
          path="/admin/incidents"
          element={
            <AppLayout>
              <AdminIncidentsPage />
            </AppLayout>
          }
        />
        <Route
          path="/admin/incidents/:incidentId"
          element={
            <AppLayout>
              <AdminIncidentDetailPage />
            </AppLayout>
          }
        />
        <Route
          path="/admin/pickups"
          element={
            <AppLayout>
              <AdminPickupQueuePage />
            </AppLayout>
          }
        />
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['ADMIN']} />}>
        <Route path="/admin/facilities" element={<AppLayout><div className="rounded-xl border border-slate-200 bg-white p-6"><h1 className="text-2xl font-semibold">Facilities</h1><p className="mt-3 text-slate-600">Facility directory and status management for the admin role.</p></div></AppLayout>} />
        <Route path="/admin/users" element={<AppLayout><div className="rounded-xl border border-slate-200 bg-white p-6"><h1 className="text-2xl font-semibold">Users</h1><p className="mt-3 text-slate-600">User administration and membership controls.</p></div></AppLayout>} />
      </Route>

      <Route path="*" element={<Navigate to={defaultPath} replace />} />
    </Routes>
  );
}

export default App;
