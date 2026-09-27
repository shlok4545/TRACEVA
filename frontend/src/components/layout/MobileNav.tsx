import type { LucideIcon } from 'lucide-react';
import { LogOut, X } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import type { User } from '../../types/auth';

type MobileNavProps = {
  open: boolean;
  onClose: () => void;
  user: User | null;
  navItems: Array<{ label: string; to: string; icon: LucideIcon }>;
  onLogout: () => Promise<void>;
};

export function MobileNav({ open, onClose, user, navItems, onLogout }: MobileNavProps) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-40 bg-slate-950/70 lg:hidden">
      <div className="h-full w-72 bg-slate-900 p-4 text-slate-100">
        <div className="mb-4 flex items-center justify-between">
          <div className="text-lg font-semibold">TRACEVA</div>
          <button type="button" onClick={onClose} className="rounded-lg border border-slate-700 p-2">
            <X size={16} />
          </button>
        </div>
        <div className="mb-4 rounded-lg border border-slate-700 bg-slate-800/70 p-3 text-sm">
          <div className="text-slate-400">Signed in as</div>
          <div className="mt-1 font-medium text-white">{user?.name ?? 'Guest'}</div>
        </div>
        <nav className="space-y-2">
          {navItems.map((link) => {
            const Icon = link.icon;
            return (
              <NavLink
                key={link.to}
                to={link.to}
                onClick={onClose}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm ${isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800'}`
                }
              >
                <Icon size={16} />
                {link.label}
              </NavLink>
            );
          })}
        </nav>
        <button type="button" onClick={() => void onLogout()} className="mt-5 flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </div>
  );
}
