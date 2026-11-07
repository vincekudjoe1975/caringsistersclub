import React from 'react';
import { History } from 'lucide-react';
import { LEVELS } from './TeamList';

const WHAT = {
  granted: (e) => `gave ${e.target.name} ${LEVELS[e.level] || 'Admin access'}`,
  preapproved: (e) => `pre-approved ${e.target.email} for Admin`,
  preapproval_removed: (e) => `removed the pre-approval for ${e.target.email}`,
  removed: (e) => `removed Admin access from ${e.target.name}`,
  to_member: (e) => `changed ${e.target.name} to a member`,
  level: (e) => `changed ${e.target.name} to ${LEVELS[e.level] || e.level}`,
};
const when = (iso) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });

export function StaffLog({ rows }) {
  return (
    <div data-testid="staff-log" className="mt-10">
      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2"><History size={18} className="text-[#B4247E]" /> Staff change log</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">Every time someone is given or loses Admin access, newest first.</p>
      <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 divide-y divide-[#3B0A2E]/8">
        {rows.length ? rows.map((e) => (
          <div key={e.id} data-testid={`staff-log-row-${e.id}`} className="p-4 flex flex-wrap items-baseline justify-between gap-2">
            <p className="text-[13.5px] text-[#241019]"><b className="text-[#3B0A2E]">{e.by.name}</b> {(WHAT[e.action] || (() => e.action))(e)}</p>
            <p className="text-[12px] text-[#241019]/50">{when(e.at)}</p>
          </div>
        )) : <p data-testid="staff-log-empty" className="p-4 text-[13px] text-[#241019]/55">No changes recorded yet. Changes from now on will appear here.</p>}
      </div>
    </div>
  );
}
