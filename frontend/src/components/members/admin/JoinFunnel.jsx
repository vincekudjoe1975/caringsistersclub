import React, { useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { UserPlus, FileText, BadgeCheck } from 'lucide-react';

const STEPS = [
  { k: 'signed_up', l: 'Signed up', icon: UserPlus },
  { k: 'applied', l: 'Applied', icon: FileText },
  { k: 'approved', l: 'Approved', icon: BadgeCheck },
];

export function JoinFunnel() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/members/funnel').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d) return null;
  return (
    <div data-testid="join-funnel" className="lg:col-span-2 bg-white rounded-2xl p-5 sm:p-6 border border-[#3B0A2E]/8">
      <div className="flex flex-wrap items-baseline justify-between gap-2 mb-4">
        <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Joining this month <span className="text-[13px] font-sans font-normal text-[#241019]/50">{d.this_month.label}</span></p>
        <p className="text-[12px] text-[#241019]/50">Compared with {d.last_month.label}</p>
      </div>
      <div className="grid grid-cols-3 gap-3">
        {STEPS.map(({ k, l, icon: Icon }) => {
          const now = d.this_month[k], before = d.last_month[k], diff = now - before;
          return (
            <div key={k} data-testid={`funnel-${k}`} className="rounded-xl bg-[#F7EFE9] p-4">
              <p className="text-[12px] font-semibold text-[#241019]/60 flex items-center gap-1.5"><Icon size={13} className="text-[#B4247E]" /> {l}</p>
              <p data-testid={`funnel-${k}-count`} className="font-serif text-[30px] text-[#3B0A2E] font-semibold leading-tight">{now}</p>
              <p data-testid={`funnel-${k}-last`} className={`text-[12px] ${diff > 0 ? 'text-[#1f7a4d]' : diff < 0 ? 'text-[#9B1C3A]' : 'text-[#241019]/50'}`}>{before} last month{diff ? ` (${diff > 0 ? '+' : ''}${diff})` : ''}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}
