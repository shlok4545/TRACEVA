import { Bell, ChevronDown, LogOut, Menu, Search, UserCircle2 } from 'lucide-react';
import { useState } from 'react';
import { Link } from 'react-router-dom';

import type { User } from '../../types/auth';
import { Button } from '../ui/Button';
import { ConnectivityIndicator } from '../ui/ConnectivityIndicator';

type TopbarProps = {
  onMenuClick?: () => void;
  user: User | null;
  onLogout: () => Promise<void>;
};

export function Topbar({ onMenuClick, user, onLogout }: TopbarProps) {
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <header className="border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur-sm sm:px-6">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={onMenuClick}
            className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700 lg:hidden"
          >
            <Menu size={18} />
          </button>

          <div className="hidden items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-500 md:flex">
            <Search size={16} />
            <input
              aria-label="Search"
              className="w-48 border-0 bg-transparent text-sm outline-none placeholder:text-slate-400"
              placeholder="Search..."
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <ConnectivityIndicator state="ONLINE" pendingActions={0} />
          <Button variant="secondary" size="sm" className="hidden sm:inline-flex">
            Quick View
          </Button>
          <Link to="/notifications" className="relative inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-700" aria-label="Open notifications">
            <Bell size={16} />
            <span className="absolute -right-1 -top-1 h-2.5 w-2.5 rounded-full bg-amber-500" />
          </Link>

          <div className="relative">
            <button type="button" onClick={() => setProfileOpen((value) => !value)} className="flex items-center gap-2 rounded-lg border border-slate-200 bg-slate-50 px-2 py-2">
              <UserCircle2 size={30} className="text-slate-600" />
              <div className="hidden sm:block text-left">
                <div className="text-sm font-medium text-slate-800">{user?.name ?? 'Guest'}</div>
                <div className="text-[11px] text-slate-500">{user?.role ?? 'Unassigned'}</div>
              </div>
              <ChevronDown size={15} className="text-slate-500" />
            </button>

            {profileOpen && (
              <div className="absolute right-0 mt-2 w-64 rounded-xl border border-slate-200 bg-white p-3 shadow-xl">
                <div className="border-b border-slate-200 pb-3">
                  <div className="text-sm font-semibold text-slate-900">{user?.name ?? 'Guest'}</div>
                  <div className="text-xs text-slate-500">{user?.role ?? 'No role'}</div>
                  <div className="mt-1 text-xs text-slate-500">{user?.facility_name ?? 'No facility assigned'}</div>
                </div>
                <div className="mt-3 space-y-2 text-sm text-slate-600">
                  <button type="button" className="flex w-full items-center justify-between rounded-lg px-2 py-2 hover:bg-slate-100">Profile <span>→</span></button>
                  <button type="button" onClick={() => void onLogout()} className="flex w-full items-center justify-between rounded-lg px-2 py-2 text-rose-600 hover:bg-rose-50">
                    Logout <LogOut size={15} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
