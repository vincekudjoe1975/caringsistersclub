import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { HeartHandshake, Plus, Trash2, Check } from 'lucide-react';
import { fmtDate } from '../fmt';

const money = (n) => `$${Number(n || 0).toFixed(2).replace(/\.00$/, '')}`;
const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const KIND = { bereavement: 'Bereavement (6.4)', illness: 'Serious illness (6.5)' };

function NewCollection({ members, onCreated }) {
  const { toast } = useToast();
  const [f, setF] = useState({ kind: 'bereavement', beneficiary_id: '', relationship: '', share: '', note: '', notify: true });
  const submit = async (e) => {
    e.preventDefault();
    try { const { data } = await api.post('/admin/members/collections', { ...f, share: Number(f.share) }); toast({ title: 'Collection opened', description: `Added to ${data.charged} sisters' balances.` }); setF({ ...f, beneficiary_id: '', relationship: '', note: '' }); onCreated(); }
    catch (ex) { toast({ title: 'Could not open collection', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <form onSubmit={submit} data-testid="collection-form" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 space-y-3 self-start">
      <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold flex items-center gap-2"><HeartHandshake size={18} className="text-[#B4247E]" /> Open a support collection</p>
      <div className="flex gap-1">{Object.entries(KIND).map(([k, l]) => <button type="button" key={k} data-testid={`collection-kind-${k}`} onClick={() => setF({ ...f, kind: k, share: k === 'illness' ? '50' : f.share })} className={`flex-1 rounded-full py-1.5 text-[12.5px] font-semibold ${f.kind === k ? 'bg-[#3B0A2E] text-white' : 'bg-[#F7EFE9] text-[#3B0A2E]'}`}>{l}</button>)}</div>
      <select data-testid="collection-beneficiary" required value={f.beneficiary_id} onChange={(e) => setF({ ...f, beneficiary_id: e.target.value })} className={`${inputCls} w-full`}>
        <option value="">Sister receiving support…</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}
      </select>
      <input data-testid="collection-relationship" placeholder={f.kind === 'bereavement' ? 'Relationship of the deceased (e.g. mother)' : 'Short description (optional)'} value={f.relationship} onChange={(e) => setF({ ...f, relationship: e.target.value })} className={`${inputCls} w-full`} />
      <input data-testid="collection-share" type="number" min="1" required placeholder="Share per member, set by the Executive Board ($)" value={f.share} onChange={(e) => setF({ ...f, share: e.target.value })} className={`${inputCls} w-full`} />
      <textarea data-testid="collection-note" rows={2} placeholder="Message to members (optional, e.g. service details)" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} className={`${inputCls} w-full`} />
      <label className="flex items-center gap-2 text-[13px] text-[#241019]/75"><input data-testid="collection-notify" type="checkbox" checked={f.notify} onChange={(e) => setF({ ...f, notify: e.target.checked })} className="accent-[#B4247E]" /> Email a notice to all members</label>
      <button data-testid="collection-create-btn" className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold flex items-center gap-1"><Plus size={14} /> Open collection</button>
    </form>
  );
}

function Payouts({ c, reload }) {
  const [p, setP] = useState({ amount: '', date: new Date().toISOString().slice(0, 10), method: 'zelle', note: '' });
  const add = async (e) => { e.preventDefault(); await api.post(`/admin/members/collections/${c.id}/payouts`, { ...p, amount: Number(p.amount) }); setP({ ...p, amount: '', note: '' }); reload(); };
  return (
    <div className="mt-4">
      <p className="text-[12px] uppercase tracking-wider text-[#241019]/50 mb-2">Paid out to {c.beneficiary_name}</p>
      {c.payouts.map((x) => (
        <div key={x.id} className="flex justify-between text-[13px] py-1"><span>{fmtDate(x.date + 'T12:00:00')} · {x.method}{x.note ? ` · ${x.note}` : ''}</span>
          <span className="flex gap-3 items-center"><b>{money(x.amount)}</b><button data-testid={`payout-del-${x.id}`} onClick={async () => { await api.delete(`/admin/members/collections/${c.id}/payouts/${x.id}`); reload(); }} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={13} /></button></span></div>
      ))}
      <form onSubmit={add} className="flex flex-wrap gap-2 mt-2">
        <input data-testid={`payout-amount-${c.id}`} type="number" min="1" required placeholder="Amount" value={p.amount} onChange={(e) => setP({ ...p, amount: e.target.value })} className={`${inputCls} w-24`} />
        <input data-testid={`payout-date-${c.id}`} type="date" value={p.date} onChange={(e) => setP({ ...p, date: e.target.value })} className={inputCls} />
        <select data-testid={`payout-method-${c.id}`} value={p.method} onChange={(e) => setP({ ...p, method: e.target.value })} className={inputCls}>{['zelle', 'check', 'cash', 'other'].map((m) => <option key={m}>{m}</option>)}</select>
        <input placeholder="Note" value={p.note} onChange={(e) => setP({ ...p, note: e.target.value })} className={`${inputCls} flex-1 min-w-[100px]`} />
        <button data-testid={`payout-add-${c.id}`} className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold">Record payout</button>
      </form>
    </div>
  );
}

function CollectionCard({ c, reload }) {
  const [show, setShow] = useState(false);
  const mark = async (uid) => { await api.post(`/admin/members/collections/${c.id}/contributors/${uid}/paid`, { method: 'cash' }); reload(); };
  const pct = c.expected ? Math.min(100, (c.collected / c.expected) * 100) : 0;
  return (
    <div data-testid={`collection-${c.id}`} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
      <div className="flex justify-between gap-3">
        <div><p className="text-[12px] text-[#B4247E] font-semibold">{KIND[c.kind]} · {fmtDate(c.created_at)} · {c.status}</p><p className="font-semibold text-[#3B0A2E]">{c.beneficiary_name}{c.relationship ? ` (${c.relationship})` : ''}: {money(c.share)} per sister</p></div>
        {c.status === 'open' && <button data-testid={`collection-close-${c.id}`} onClick={async () => { await api.post(`/admin/members/collections/${c.id}/close`); reload(); }} className="text-[12.5px] font-semibold text-[#241019]/55 shrink-0">Mark complete</button>}
      </div>
      <div className="grid grid-cols-4 gap-2 mt-3 text-center">
        {[['Expected', c.expected], ['Collected', c.collected], ['Paid out', c.paid_out], ['On hand', c.available]].map(([l, v]) => (
          <div key={l} className="bg-[#F7EFE9] rounded-lg py-2"><p className="text-[11px] text-[#241019]/55">{l}</p><p data-testid={`collection-${l.toLowerCase().replace(' ', '-')}-${c.id}`} className="font-semibold text-[#3B0A2E]">{money(v)}</p></div>
        ))}
      </div>
      <div className="h-1.5 bg-[#F7EFE9] rounded-full mt-3 overflow-hidden"><div className="h-full bg-[#B4247E] transition-[width] duration-700" style={{ width: `${pct}%` }} /></div>
      <button data-testid={`collection-toggle-${c.id}`} onClick={() => setShow(!show)} className="text-[12.5px] font-semibold text-[#B4247E] mt-3">{show ? 'Hide details' : `Contributors (${c.contributors.filter((x) => x.paid).length}/${c.contributors.length} paid) & payouts`}</button>
      {show && (
        <>
          <div className="mt-3 max-h-60 overflow-auto">
            {c.contributors.map((x) => (
              <div key={x.user_id} className="flex justify-between items-center text-[13px] py-1 border-b border-[#3B0A2E]/6">
                <span>{x.name}</span>
                {x.paid ? <span className="text-green-700 flex items-center gap-1 text-[12px]"><Check size={13} /> {x.marked ? 'Paid' : 'Covered (account paid in full)'}</span>
                  : <button data-testid={`contrib-paid-${c.id}-${x.user_id}`} onClick={() => mark(x.user_id)} className="text-[12px] font-semibold text-[#B4247E]">Mark paid (cash)</button>}
              </div>
            ))}
          </div>
          <Payouts c={c} reload={reload} />
        </>
      )}
    </div>
  );
}

export function AdminCollections() {
  const [rows, setRows] = useState([]);
  const [members, setMembers] = useState([]);
  const load = useCallback(() => api.get('/admin/members/collections').then(({ data }) => setRows(data)), []);
  useEffect(() => { load(); api.get('/admin/members').then(({ data }) => setMembers(data.members.filter((m) => m.status === 'active'))); }, [load]);
  return (
    <div className="grid lg:grid-cols-[1fr_1.4fr] gap-6" data-testid="admin-collections">
      <NewCollection members={members} onCreated={load} />
      <div className="space-y-3">
        {rows.map((c) => <CollectionCard key={c.id} c={c} reload={load} />)}
        {!rows.length && <p className="text-[13.5px] text-[#241019]/50">No support collections yet.</p>}
      </div>
    </div>
  );
}
