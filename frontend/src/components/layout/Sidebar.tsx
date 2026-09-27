import type { LucideIcon } from 'lucide-react';
import { Bell, LogOut, ShieldCheck } from 'lucide-react';
import { NavLink } from 'react-router-dom';

import type { User } from '../../types/auth';

type SidebarProps = {
  user: User | null;
  navItems: Array<{ label: string; to: string; icon: LucideIcon }>;
  onLogout: () => Promise<void>;
};

export function Sidebar({ user, navItems, onLogout }: SidebarProps) {
  return (
    <aside className="hidden fixed inset-y-0 left-0 z-40 w-72 flex-col border-r border-slate-200 bg-slate-950 text-slate-100 lg:block">
      <div className="flex items-center gap-3 border-b border-slate-800 px-6 py-5">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-500/20 text-lg font-semibold text-emerald-300">T</div>
        <div>
          <div className="text-lg font-semibold">TRACEVA</div>
          <div className="text-xs text-slate-400">Track. Verify. Protect.</div>
        </div>
      </div>

      <nav className="flex-1 space-y-4 p-4">
        <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.18em] text-slate-400">Active role</div>
          <div className="mt-2 flex items-center gap-2 text-sm font-medium text-slate-100">
            <ShieldCheck size={15} className="text-emerald-300" />
            {user?.role ?? 'Guest'}
          </div>
        </div>

        <div className="space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition ${
                    isActive ? 'bg-slate-800 text-white' : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  }`
                }
              >
                <Icon size={16} />
                {item.label}
              </NavLink>
            );
          })}
        </div>
      </nav>

      <div className="border-t border-slate-800 p-4 space-y-2">
        <NavLink to="/notifications" className={({ isActive }) => `flex w-full items-center justify-center gap-2 rounded-lg border px-3 py-2 text-sm ${isActive ? 'border-emerald-500 bg-slate-800 text-white' : 'border-slate-700 text-slate-200 hover:bg-slate-800'}`}>
          <Bell size={16} />
          Notifications
        </NavLink>
        <button type="button" onClick={() => void onLogout()} className="flex w-full items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200 hover:bg-slate-800">
          <LogOut size={16} />
          Logout
        </button>
      </div>
    </aside>
  );
}
