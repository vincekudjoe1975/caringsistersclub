import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { Smartphone, Send, Loader2, Check } from 'lucide-react';

const recent = (iso) => iso && Date.now() - new Date(iso).getTime() < 7 * 864e5;

export function AppInstalls({ toast }) {
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState('');
  const load = useCallback(() => api.get('/admin/members/app-installs').then(({ data }) => setD(data)).catch(() => setD({ total: 0, installed: 0, rows: [] })), []);
  useEffect(() => { load(); }, [load]);
  const nudge = async (body, key) => {
    setBusy(key);
    try { const { data } = await api.post('/admin/members/app-nudge', body); toast({ title: data.sent ? `Nudge sent to ${data.sent} sister${data.sent === 1 ? '' : 's'}` : 'No one to nudge right now', description: data.sent ? undefined : 'Sisters nudged in the last 7 days are skipped.' }); load(); }
    catch (e) { toast({ title: 'Could not send', description: e?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  if (!d) return <Loader2 className="animate-spin text-[#B4247E]" size={18} />;
  const missing = d.rows.filter((r) => !r.app_installed_at);
  const pct = d.total ? Math.round((d.installed / d.total) * 100) : 0;
  return (
    <div data-testid="app-installs">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p data-testid="app-installs-count" className="flex items-center gap-2 text-[14px] text-[#3B0A2E]"><Smartphone size={16} className="text-[#B4247E]" /><b>{d.installed} of {d.total}</b> sisters installed the app ({pct}%)</p>
        {missing.length > 0 && <button data-testid="app-nudge-all-btn" disabled={busy === 'all' || missing.every((r) => recent(r.app_nudged_at))} title={missing.every((r) => recent(r.app_nudged_at)) ? 'Everyone was nudged in the last 7 days' : undefined} onClick={() => nudge({ all: true }, 'all')} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy === 'all' ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Nudge all</button>}
      </div>
      <div className="h-2 rounded-full bg-[#F7EFE9] overflow-hidden mb-4"><div className="h-full bg-[#B4247E] transition-[width] duration-700" style={{ width: `${pct}%` }} /></div>
      {!missing.length ? <p data-testid="app-installs-all-done" className="text-[13.5px] text-[#3c7a2f] flex items-center gap-1.5"><Check size={15} /> Every sister has the app.</p> : (
        <ul className="divide-y divide-[#3B0A2E]/8 max-h-[320px] overflow-y-auto">
          {missing.map((r) => (
            <li key={r.user_id} data-testid={`app-missing-${r.user_id}`} className="py-2.5 flex items-center justify-between gap-3">
              <div className="min-w-0"><p className="text-[14px] font-semibold text-[#3B0A2E] truncate">{r.name || r.email}</p><p className="text-[12px] text-[#241019]/55 truncate">{r.email}{r.app_nudged_at ? ` · nudged ${new Date(r.app_nudged_at).toLocaleDateString()}` : ''}</p></div>
              <button data-testid={`app-nudge-${r.user_id}`} disabled={recent(r.app_nudged_at) || busy === r.user_id} onClick={() => nudge({ user_ids: [r.user_id] }, r.user_id)} className="rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] hover:bg-[#F7EFE9] disabled:opacity-45 shrink-0">{recent(r.app_nudged_at) ? 'Nudged' : 'Nudge'}</button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
