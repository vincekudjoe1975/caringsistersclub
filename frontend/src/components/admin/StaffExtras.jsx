import React, { useState } from 'react';
import { format } from 'date-fns';
import { CalendarX2, BadgeCheck, X } from 'lucide-react';
import { Popover, PopoverContent, PopoverTrigger } from '../ui/popover';
import { Calendar } from '../ui/calendar';

const DAY = 86400000;
export const ago = (iso) => {
  if (!iso) return null;
  const d = Math.floor((Date.now() - new Date(iso).getTime()) / DAY);
  return d <= 0 ? 'today' : d === 1 ? 'yesterday' : `${d} days ago`;
};
export const fmtDay = (d) => new Date(`${d}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
const tomorrowET = () => { const t = new Date(`${new Date().toLocaleDateString('en-CA', { timeZone: 'America/New_York' })}T00:00:00`); t.setDate(t.getDate() + 1); return t; };

export function StaffActivity({ u }) {
  const stale = !u.admin_last_seen_at || Date.now() - new Date(u.admin_last_seen_at).getTime() > 30 * DAY;
  return (
    <p data-testid={`team-activity-${u.user_id}`} className="text-[11.5px] text-[#241019]/50 mt-0.5 flex flex-wrap items-center gap-1.5">
      {u.admin_last_seen_at ? `Opened Admin ${ago(u.admin_last_seen_at)}` : 'Has not opened Admin yet'}
      {stale && <span data-testid={`team-stale-${u.user_id}`} className="px-2 py-px rounded-full bg-[#FDECEF] text-[#9B1C3A] font-semibold">Not used lately</span>}
      {u.staff_expires_on && <span data-testid={`team-expiry-tag-${u.user_id}`} className="px-2 py-px rounded-full bg-[#FFF4DD] text-[#8a6d2f] font-semibold">Access ends {fmtDay(u.staff_expires_on)}</span>}
      {u.club_team_badge && <span className="px-2 py-px rounded-full bg-[#F7EFE9] text-[#B4247E] font-semibold">Club team badge</span>}
    </p>
  );
}

function EndDate({ u, onExpiry }) {
  const [open, setOpen] = useState(false);
  const min = tomorrowET();
  return (
    <span className="flex items-center gap-1.5"><CalendarX2 size={13} className="text-[#B4247E]" /> Access ends
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button data-testid={`team-expiry-input-${u.user_id}`} className="rounded-lg border border-[#3B0A2E]/15 px-2.5 py-1 text-[12px] font-semibold text-[#3B0A2E] hover:border-[#B4247E]">{u.staff_expires_on ? fmtDay(u.staff_expires_on) : 'No end date'}</button>
        </PopoverTrigger>
        <PopoverContent className="w-auto p-0" align="start">
          <Calendar data-testid={`team-expiry-calendar-${u.user_id}`} mode="single" selected={u.staff_expires_on ? new Date(`${u.staff_expires_on}T12:00:00`) : undefined}
            disabled={{ before: min }} defaultMonth={u.staff_expires_on ? new Date(`${u.staff_expires_on}T12:00:00`) : min}
            onSelect={(d) => { if (d) { setOpen(false); onExpiry(u, format(d, 'yyyy-MM-dd')); } }} initialFocus />
        </PopoverContent>
      </Popover>
      {u.staff_expires_on && <button data-testid={`team-expiry-clear-${u.user_id}`} onClick={() => onExpiry(u, null)} aria-label="Keep access with no end date" className="p-1 hover:text-[#B4247E]"><X size={13} /></button>}
    </span>
  );
}

export function OwnerControls({ u, onExpiry, onBadge }) {
  return (
    <div data-testid={`team-owner-controls-${u.user_id}`} className="w-full flex flex-wrap items-center gap-3 pl-12 text-[12px] text-[#241019]/65">
      <EndDate u={u} onExpiry={onExpiry} />
      <button data-testid={`team-badge-toggle-${u.user_id}`} onClick={() => onBadge(u, !u.club_team_badge)}
        className={`rounded-full px-3 py-1 font-semibold flex items-center gap-1 border transition-colors ${u.club_team_badge ? 'bg-[#B4247E] text-white border-[#B4247E]' : 'border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E]'}`}>
        <BadgeCheck size={13} /> {u.club_team_badge ? 'Club team badge: on' : 'Show Club team badge'}
      </button>
    </div>
  );
}
