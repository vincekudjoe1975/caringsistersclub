import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Send, Wand2, Loader2 } from 'lucide-react';
import { fmtDate } from '../fmt';

const money = (n) => `$${Number(n || 0).toFixed(2)}`;
const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-1.5 text-[13px] focus:outline-none focus:border-[#B4247E]';

function Notices() {
  const { toast } = useToast();
  const [p, setP] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/members/referrers/preview').then(({ data }) => setP(data)), []);
  useEffect(() => { load(); }, [load]);
  const send = async () => {
    if (!window.confirm(`Email each referrer about her sponsored sisters' unpaid ${p.year} balances?`)) return;
    setBusy(true);
    try { const { data } = await api.post('/admin/members/referrers/notify', { year: p.year }); toast({ title: `Sent ${data.sent} notice${data.sent === 1 ? '' : 's'}` }); load(); } finally { setBusy(false); }
  };
  if (!p) return null;
  return (
    <div data-testid="referrer-notices" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 self-start">
      <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Year-end sponsor notices</p>
      <p className="text-[12.5px] text-[#241019]/55 mb-3">Sent automatically on January 2 for the previous year (Section 5.4). Preview for {p.year}:</p>
      {!p.groups.length ? <p className="text-[13px] text-[#241019]/50">No sponsored sisters with unpaid {p.year} balances.</p> : p.groups.map((g) => (
        <div key={g.referrer_id} data-testid={`notice-group-${g.referrer_id}`} className="py-2 border-b border-[#3B0A2E]/8 last:border-0">
          <p className="text-[13.5px] font-semibold text-[#3B0A2E]">{g.referrer_name}</p>
          {g.sisters.map((s, i) => <p key={i} className="text-[12.5px] text-[#241019]/70">{s.name}: {money(s.balance)}{s.status === 'ended' ? ' (left)' : ''}</p>)}
        </div>
      ))}
      <button data-testid="referrer-notify-btn" onClick={send} disabled={busy || !p.groups.length} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold mt-4 flex items-center gap-1.5 disabled:opacity-50">{busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send notices now</button>
      {p.runs[0] && <p className="text-[12px] text-[#241019]/50 mt-2">Last sent {fmtDate(p.runs[0].at)} ({p.runs[0].sent} emails, {p.runs[0].year})</p>}
    </div>
  );
}

export function AdminReferrers() {
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/admin/members/referrers').then(({ data }) => setD(data)), []);
  useEffect(() => { load(); }, [load]);
  const link = async (uid, referrer_id) => { await api.put(`/admin/members/${uid}/referrer`, { referrer_id: referrer_id || null }); load(); };
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div className="grid lg:grid-cols-[1.5fr_1fr] gap-6" data-testid="admin-referrers">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
        <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Who referred whom</p>
        <p className="text-[12.5px] text-[#241019]/55 mb-4">Link each sister to the member who sponsored her. Suggestions come from the name typed on her application.</p>
        {d.rows.map((r) => (
          <div key={r.user_id} data-testid={`ref-row-${r.user_id}`} className="py-2.5 border-b border-[#3B0A2E]/8 last:border-0 flex flex-wrap items-center gap-2">
            <div className="flex-1 min-w-[160px]"><p className="text-[13.5px] font-semibold text-[#3B0A2E]">{r.name}</p><p className="text-[12px] text-[#241019]/50">{r.referred_by ? `Typed: "${r.referred_by}"` : 'No referrer typed'}</p></div>
            {r.suggestion && <button data-testid={`ref-suggest-${r.user_id}`} onClick={() => link(r.user_id, r.suggestion.user_id)} className="text-[12px] font-semibold text-[#B4247E] flex items-center gap-1"><Wand2 size={12} /> Use {r.suggestion.name}</button>}
            <select data-testid={`ref-select-${r.user_id}`} value={r.referrer_id || ''} onChange={(e) => link(r.user_id, e.target.value)} className={inputCls}>
              <option value="">Not linked</option>{d.members.filter((m) => m.user_id !== r.user_id).map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
            </select>
          </div>
        ))}
        {!d.rows.length && <p className="text-[13px] text-[#241019]/50">No members yet.</p>}
      </div>
      <Notices />
    </div>
  );
}
