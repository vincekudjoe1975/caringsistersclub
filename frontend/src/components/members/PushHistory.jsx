import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';

const KINDS = [['', 'All'], ['announcement', 'Announcements'], ['prayer', 'Prayer'], ['event', 'Events'], ['vote', 'Votes'], ['birthday', 'Birthdays'], ['custom', 'Custom']];
const LABEL = Object.fromEntries(KINDS);
const when = (iso) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

export const PushHistory = ({ refresh }) => {
  const [kind, setKind] = useState('');
  const [rows, setRows] = useState(null);
  const load = useCallback(() => api.get('/admin/members/push/history', { params: { kind } }).then(({ data }) => setRows(data)).catch(() => setRows([])), [kind]);
  useEffect(() => { load(); }, [load, refresh]);
  return (
    <div data-testid="push-history" className="mt-6 pt-5 border-t border-[#3B0A2E]/10">
      <p className="font-semibold text-[#3B0A2E] mb-3">Alert history</p>
      <div className="flex flex-wrap gap-1.5 mb-3">
        {KINDS.map(([k, l]) => (
          <button key={k || 'all'} type="button" data-testid={`push-history-filter-${k || 'all'}`} onClick={() => setKind(k)}
            className={`rounded-full px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${kind === k ? 'bg-[#3B0A2E] text-white' : 'bg-white border border-[#3B0A2E]/15 text-[#3B0A2E]'}`}>{l}</button>
        ))}
      </div>
      {rows === null ? <p className="text-[13px] text-[#241019]/50">Loading…</p> : !rows.length ? <p data-testid="push-history-empty" className="text-[13px] text-[#241019]/55">No alerts sent yet.</p> : (
        <div className="max-h-80 overflow-y-auto">
          {rows.map((r) => (
            <div key={r.id} data-testid={`push-history-row-${r.id}`} className="py-2.5 border-t border-[#3B0A2E]/8 text-[13px]">
              <div className="flex items-start justify-between gap-3">
                <p className="text-[#3B0A2E] font-semibold min-w-0 break-words">{r.title}</p>
                <span className="shrink-0 rounded-full px-2 py-0.5 text-[12px] bg-[#F7EFE9] text-[#B4247E] font-semibold">{LABEL[r.kind] || r.kind}</span>
              </div>
              <p className="text-[#241019]/55 mt-0.5">{when(r.sent_at)} · <span data-testid={`push-history-reached-${r.id}`}>{r.delivered} phone{r.delivered === 1 ? '' : 's'} reached</span>{r.failed ? ` · ${r.failed} failed` : ''}{r.expired ? ` · ${r.expired} expired removed` : ''}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
