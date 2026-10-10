import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { Plus, Trash2, Cake, X } from 'lucide-react';
import { fmtDate } from '../fmt';

const money = (n) => `$${Number(n || 0).toFixed(2).replace(/\.00$/, '')}`;
const ST = { paid: 'bg-green-100 text-green-800', due: 'bg-amber-100 text-amber-800', overdue: 'bg-red-100 text-red-700' };
const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';

function LedgerPanel({ row, year, onClose, onChanged }) {
  const [s, setS] = useState(null);
  const [f, setF] = useState({ amount: '', method: 'cash', kind: 'dues', note: '', type: 'payment' });
  const load = useCallback(() => api.get(`/admin/members/${row.user_id}/ledger`, { params: { year } }).then(({ data }) => setS(data)), [row.user_id, year]);
  useEffect(() => { load(); }, [load]);
  const add = async (e) => {
    e.preventDefault();
    const path = f.type === 'payment' ? 'payments' : 'charges';
    await api.post(`/admin/members/${row.user_id}/${path}`, { amount: Number(f.amount), method: f.method, kind: f.type === 'payment' ? f.kind : (f.kind === 'dues' ? 'other' : f.kind), note: f.note, year });
    setF({ ...f, amount: '', note: '' }); load(); onChanged();
  };
  return (
    <div data-testid="ledger-panel" className="bg-[#faf2f7] rounded-2xl p-5 mt-3">
      <div className="flex justify-between items-center mb-3"><p className="font-semibold text-[#3B0A2E]">{row.name}: {year} ledger</p><button data-testid="ledger-close" onClick={onClose}><X size={16} /></button></div>
      <form onSubmit={add} className="flex flex-wrap gap-2 mb-4">
        <select data-testid="ledger-type" value={f.type} onChange={(e) => setF({ ...f, type: e.target.value })} className={inputCls}><option value="payment">Record payment</option><option value="charge">Add charge</option></select>
        <input data-testid="ledger-amount" type="number" min="1" placeholder="Amount" value={f.amount} onChange={(e) => setF({ ...f, amount: e.target.value })} className={`${inputCls} w-28`} required />
        {f.type === 'payment' && <select data-testid="ledger-method" value={f.method} onChange={(e) => setF({ ...f, method: e.target.value })} className={inputCls}>{['cash', 'zelle', 'check', 'other'].map((m) => <option key={m} value={m}>{m[0].toUpperCase() + m.slice(1)}</option>)}</select>}
        <select data-testid="ledger-kind" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={inputCls}>
          {(f.type === 'payment' ? ['dues', 'registration', 'fine', 'birthday'] : ['registration', 'fine', 'birthday', 'other']).map((k) => <option key={k} value={k}>{k[0].toUpperCase() + k.slice(1)}</option>)}
        </select>
        <input data-testid="ledger-note" placeholder="Note (optional)" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} className={`${inputCls} flex-1 min-w-[140px]`} />
        <button data-testid="ledger-add-btn" className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1"><Plus size={14} /> Save</button>
      </form>
      {s && (s.ledger.length ? s.ledger.map((e) => (
        <div key={e.id} className="flex justify-between items-center text-[13px] py-1.5 border-b border-[#3B0A2E]/8 last:border-0">
          <span>{fmtDate(e.created_at)} · {e.note}{e.method ? ` (${e.method})` : ''}</span>
          <span className="flex items-center gap-3"><b className={e.direction === 'payment' ? 'text-green-700' : ''}>{e.direction === 'payment' ? '−' : '+'}{money(e.amount)}</b>
            {e.method !== 'card' && <button data-testid={`ledger-del-${e.id}`} onClick={async () => { await api.delete(`/admin/members/ledger/${e.id}`); load(); onChanged(); }} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={13} /></button>}</span>
        </div>
      )) : <p className="text-[13px] text-[#241019]/50">No entries yet. Annual dues of {money(s.dues_expected)} are counted automatically.</p>)}
    </div>
  );
}

function BirthdayCollections({ onChanged }) {
  const [rows, setRows] = useState([]);
  const [started, setStarted] = useState([]);
  const load = useCallback(() => {
    api.get('/members/birthdays').then(({ data }) => setRows(data));
    api.get('/admin/members/birthday-collections').then(({ data }) => setStarted(data.map((c) => c.user_id)));
  }, []);
  useEffect(() => { load(); }, [load]);
  if (!rows.length) return null;
  const start = async (uid) => { await api.post('/admin/members/birthday-collection', { user_id: uid, amount: 25 }); load(); onChanged(); };
  return (
    <div data-testid="birthday-collections" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-5">
      <p className="font-semibold text-[#3B0A2E] mb-3 flex items-center gap-2"><Cake size={16} className="text-[#B4247E]" /> This month's birthdays: $25 contribution (Section 6.3)</p>
      {rows.map((b) => (
        <div key={b.user_id} className="flex justify-between items-center text-[13.5px] py-1.5">
          <span>{b.name} · day {b.day}</span>
          {started.includes(b.user_id) ? <span className="text-green-700 text-[12.5px] font-semibold">Collection added to members' balances</span>
            : <button data-testid={`bday-collect-${b.user_id}`} onClick={() => start(b.user_id)} className="text-[12.5px] font-semibold text-[#B4247E]">Start $25 collection</button>}
        </div>
      ))}
    </div>
  );
}

export function AdminDues() {
  const [year, setYear] = useState(new Date().getFullYear());
  const [d, setD] = useState(null);
  const [filter, setFilter] = useState('all');
  const [open, setOpen] = useState(null);
  const load = useCallback(() => api.get('/admin/members/dues', { params: { year } }).then(({ data }) => setD(data)), [year]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  const rows = d.rows.filter((r) => filter === 'all' || (filter === 'unpaid' ? r.dues_status !== 'paid' : r.dues_status === filter));
  return (
    <div data-testid="admin-dues">
      <BirthdayCollections onChanged={load} />
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5">
        {[['Collected', money(d.totals.collected)], ['Outstanding', money(d.totals.outstanding)], ['Overdue members', d.totals.overdue], ['Paid in full', d.totals.paid_in_full]].map(([l, v]) => (
          <div key={l} className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8"><p className="text-[12px] text-[#241019]/55">{l}</p><p data-testid={`dues-total-${l.toLowerCase().replace(/\s/g, '-')}`} className="font-serif text-[24px] text-[#3B0A2E] font-semibold">{v}</p></div>
        ))}
      </div>
      <div className="flex flex-wrap items-center gap-2 mb-4">
        <select data-testid="dues-year" value={year} onChange={(e) => setYear(Number(e.target.value))} className={inputCls}>{[0, 1, 2].map((i) => { const y = new Date().getFullYear() - i; return <option key={y} value={y}>{y}</option>; })}</select>
        {['all', 'unpaid', 'overdue', 'paid'].map((k) => <button key={k} data-testid={`dues-filter-${k}`} onClick={() => setFilter(k)} className={`rounded-full px-4 py-1.5 text-[13px] font-semibold capitalize ${filter === k ? 'bg-[#3B0A2E] text-white' : 'bg-white border border-[#3B0A2E]/15 text-[#3B0A2E]'}`}>{k}</button>)}
        <span className="text-[12.5px] text-[#241019]/50 ml-auto">Dues are due in full by January 31 ($10 × months of membership)</span>
      </div>
      <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 divide-y divide-[#3B0A2E]/8">
        {rows.map((r) => (
          <div key={r.user_id} data-testid={`dues-row-${r.user_id}`} className="p-4">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex-1 min-w-[160px]"><p className="font-semibold text-[#3B0A2E] text-[14px]">{r.name}</p><p className="text-[12px] text-[#241019]/50">{r.email}</p></div>
              <span className="text-[13px] text-[#241019]/70">Paid {money(r.paid)} / {money(r.dues_expected + r.charges)}</span>
              <b className="text-[14px] text-[#B4247E] w-20 text-right">{money(r.balance)}</b>
              <span className={`text-[11.5px] font-semibold px-2.5 py-0.5 rounded-full ${ST[r.dues_status]}`}>{r.dues_status}</span>
              <button data-testid={`dues-open-${r.user_id}`} onClick={() => setOpen(open === r.user_id ? null : r.user_id)} className="text-[12.5px] font-semibold text-[#B4247E]">{open === r.user_id ? 'Close' : 'Ledger'}</button>
            </div>
            {open === r.user_id && <LedgerPanel row={r} year={year} onClose={() => setOpen(null)} onChanged={load} />}
          </div>
        ))}
        {!rows.length && <p className="p-6 text-center text-[13.5px] text-[#241019]/50">No members match this filter.</p>}
      </div>
    </div>
  );
}
