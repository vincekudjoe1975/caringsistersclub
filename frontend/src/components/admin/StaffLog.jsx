import React, { useState } from 'react';
import { History, Undo2, Loader2 } from 'lucide-react';
import { LEVELS } from './TeamList';

const WHAT = {
  granted: (e) => `gave ${e.target.name} ${LEVELS[e.level] || 'Admin access'}`,
  preapproved: (e) => `pre-approved ${e.target.email} for Admin`,
  preapproval_removed: (e) => `removed the pre-approval for ${e.target.email}`,
  removed: (e) => `removed Admin access from ${e.target.name}`,
  to_member: (e) => `changed ${e.target.name} to a member`,
  level: (e) => `changed ${e.target.name} to ${LEVELS[e.level] || e.level}`,
  undo: (e) => `undid "${(WHAT[e.undid?.action] || (() => 'a change'))({ ...e, level: e.undid?.level })}"`,
};
const when = (iso) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });

function LogRow({ e, onUndo }) {
  const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); await onUndo(e); setBusy(false); };
  return (
    <div data-testid={`staff-log-row-${e.id}`} className="p-4 flex flex-wrap items-center justify-between gap-2">
      <div className="min-w-0">
        <p className={`text-[13.5px] text-[#241019] ${e.undone_at ? 'line-through opacity-60' : ''}`}><b className="text-[#3B0A2E]">{e.by.name}</b> {(WHAT[e.action] || (() => e.action))(e)}</p>
        <p className="text-[12px] text-[#241019]/50">{when(e.at)}{e.undone_at && <span data-testid={`staff-log-undone-${e.id}`}> · Undone by {e.undone_by?.name}</span>}</p>
      </div>
      {!e.undo_block && (
        <button data-testid={`staff-log-undo-${e.id}`} disabled={busy} onClick={go} className="rounded-full px-3 py-1.5 text-[12px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] flex items-center gap-1 transition-colors disabled:opacity-60">
          {busy ? <Loader2 size={13} className="animate-spin" /> : <Undo2 size={13} />} Undo
        </button>
      )}
    </div>
  );
}

export function StaffLog({ rows, onUndo }) {
  const [all, setAll] = useState(false);
  const shown = all ? rows : rows.slice(0, 10);
  return (
    <div data-testid="staff-log" className="mt-10">
      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2"><History size={18} className="text-[#B4247E]" /> Staff change log</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">Every time someone is given or loses Admin access, newest first. Undo works on a person's latest change from the last 7 days.</p>
      <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 divide-y divide-[#3B0A2E]/8">
        {shown.length ? shown.map((e) => <LogRow key={e.id} e={e} onUndo={onUndo} />)
          : <p data-testid="staff-log-empty" className="p-4 text-[13px] text-[#241019]/55">No changes recorded yet. Changes from now on will appear here.</p>}
      </div>
      {rows.length > 10 && (
        <button data-testid="staff-log-toggle" onClick={() => setAll(!all)} className="mt-3 text-[13px] font-semibold text-[#B4247E] hover:underline">{all ? 'Show fewer' : `Show all ${rows.length} changes`}</button>
      )}
    </div>
  );
}
