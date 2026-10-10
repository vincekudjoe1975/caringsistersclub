import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { CheckCircle2, Undo2, ClipboardCheck } from 'lucide-react';
import { fmtDate } from '../fmt';

const money = (n) => `$${Number(n || 0).toFixed(2).replace(/\.00$/, '')}`;
const LISTS = [
  { k: 'applications', t: 'New registrations', d: 'Section 5.1: new members are registered in December.', actions: [['approve', 'Approve'], ['decline', 'Decline']], info: (i) => `${i.city || ''}${i.referred_by ? ` · referred by ${i.referred_by}` : ''}` },
  { k: 'leaving', t: 'Members asking to leave', d: 'Voluntary terminations take effect December 31.', actions: [['end', 'Confirm leaving'], ['keep', 'Keep member']], info: (i) => i.reason || 'No reason given' },
  { k: 'ending', t: 'Ending: 4+ missed meetings', d: 'Article V: terminated at the end of the year.', actions: [['end', 'Confirm ending'], ['keep', 'Excuse & keep']], info: (i) => `${i.absences} meetings missed this year` },
  { k: 'unpaid', t: 'Unpaid balances', d: 'Section 5.4: unpaid liabilities of members who leave are borne by their referrer.', actions: [['reviewed', 'Mark reviewed']], info: (i) => `${money(i.balance)} owed${i.referred_by ? ` · referrer: ${i.referred_by}` : ''}` },
];
const DONE = { approve: 'Approved', decline: 'Declined', end: 'Ends Dec 31', keep: 'Kept', reviewed: 'Reviewed' };

export function AdminDecember() {
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/admin/members/december').then(({ data }) => setD(data)), []);
  useEffect(() => { load(); }, [load]);
  const act = async (key, decision) => {
    try { await api.post('/admin/members/december', { key, decision }); load(); }
    catch (ex) { toast({ title: 'Failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const undo = async (key) => { await api.delete('/admin/members/december', { params: { key } }); load(); };
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  const pct = d.total ? (d.completed / d.total) * 100 : 100;
  return (
    <div data-testid="admin-december">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-5 flex flex-wrap items-center gap-5">
        <ClipboardCheck size={28} className="text-[#B4247E]" />
        <div className="flex-1 min-w-[200px]">
          <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold">December {d.year} renewal checklist</p>
          <p className="text-[12.5px] text-[#241019]/55">Members confirmed as leaving or ending are deactivated automatically on December 31.</p>
          <div className="h-1.5 bg-[#F7EFE9] rounded-full mt-2 overflow-hidden"><div className="h-full bg-[#B4247E] transition-[width] duration-700" style={{ width: `${pct}%` }} /></div>
        </div>
        <p data-testid="december-progress" className="font-semibold text-[#3B0A2E]">{d.completed} / {d.total} done</p>
      </div>
      <div className="grid lg:grid-cols-2 gap-5">
        {LISTS.map((L) => (
          <div key={L.k} data-testid={`december-${L.k}`} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
            <p className="font-semibold text-[#3B0A2E]">{L.t} <span className="text-[#241019]/40">({d.lists[L.k].length})</span></p>
            <p className="text-[12px] text-[#241019]/50 mb-3">{L.d}</p>
            {!d.lists[L.k].length && <p className="text-[13px] text-[#241019]/45">Nothing to review.</p>}
            {d.lists[L.k].map((i) => (
              <div key={i.key} data-testid={`dec-item-${i.key}`} className="py-2 border-b border-[#3B0A2E]/6 last:border-0 flex flex-wrap items-center gap-2">
                <div className="flex-1 min-w-[150px]"><p className="text-[13.5px] font-semibold text-[#241019]">{i.name}</p><p className="text-[12px] text-[#241019]/55">{L.info(i)}</p></div>
                {i.done ? (
                  <span className="flex items-center gap-2 text-[12px]"><span className="text-green-700 font-semibold flex items-center gap-1"><CheckCircle2 size={13} /> {DONE[i.done.decision]}</span><span className="text-[#241019]/40">{i.done.by} · {fmtDate(i.done.at)}</span>
                    {L.k !== 'applications' && <button data-testid={`dec-undo-${i.key}`} onClick={() => undo(i.key)} className="text-[#241019]/40 hover:text-[#B4247E]"><Undo2 size={13} /></button>}</span>
                ) : L.actions.map(([a, l], idx) => (
                  <button key={a} data-testid={`dec-${a}-${i.key}`} onClick={() => act(i.key, a)} className={`rounded-full px-3 py-1 text-[12px] font-semibold ${idx === 0 ? 'btn-magenta' : 'border border-[#3B0A2E]/15 text-[#3B0A2E]'}`}>{l}</button>
                ))}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
