import type { LucideIcon } from 'lucide-react';
import {
  BarChart3,
  Bell,
  Building2,
  ClipboardList,
  FileBarChart2,
  FlaskConical,
  MapPinned,
  ShieldCheck,
  Truck,
  UserCog,
} from 'lucide-react';

export const roleNavigation: Record<string, Array<{ label: string; to: string; icon: LucideIcon }>> = {
  ADMIN: [
    { label: 'Dashboard', to: '/dashboard', icon: BarChart3 },
    { label: 'Facilities', to: '/admin/facilities', icon: Building2 },
    { label: 'Users', to: '/admin/users', icon: UserCog },
    { label: 'Compliance', to: '/admin/compliance', icon: ShieldCheck },
    { label: 'Incidents', to: '/admin/incidents', icon: Bell },
  ],
  WARD_STAFF: [
    { label: 'Dashboard', to: '/dashboard', icon: BarChart3 },
    { label: 'Waste Entry', to: '/ward/waste-entry', icon: ClipboardList },
    { label: 'Passports', to: '/ward/passports', icon: FlaskConical },
    { label: 'Incidents', to: '/admin/incidents', icon: Bell },
  ],
  COLLECTOR: [
    { label: 'Assignments', to: '/collector/assignments', icon: MapPinned },
    { label: 'Scan', to: '/collector/scan', icon: Truck },
    { label: 'Routes', to: '/collector/assignments', icon: FileBarChart2 },
  ],
  TREATMENT_FACILITY: [
    { label: 'Receiving', to: '/facility/receiving', icon: Building2 },
    { label: 'Treatment', to: '/facility/treatment', icon: ShieldCheck },
    { label: 'Compliance', to: '/admin/compliance', icon: FileBarChart2 },
  ],
  REGULATOR: [
    { label: 'Dashboard', to: '/dashboard', icon: BarChart3 },
    { label: 'Compliance', to: '/admin/compliance', icon: ShieldCheck },
    { label: 'Incidents', to: '/admin/incidents', icon: Bell },
    { label: 'Reports', to: '/admin/compliance', icon: FileBarChart2 },
  ],
};

export const defaultDashboardByRole: Record<string, string> = {
  ADMIN: '/dashboard',
  WARD_STAFF: '/dashboard',
  COLLECTOR: '/collector/assignments',
  TREATMENT_FACILITY: '/facility/receiving',
  REGULATOR: '/admin/compliance',
};
