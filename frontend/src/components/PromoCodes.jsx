import React, { useCallback, useEffect, useState } from 'react';
import { Tag, Trash2, Loader2, X } from 'lucide-react';
import { api } from '../lib/api';

const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';
const EMPTY = { code: '', kind: 'percent', value: 10, event_id: '', max_uses: 0, expires: '' };

export const PromoCodes = ({ events, onClose, toast }) => {
  const [rows, setRows] = useState([]);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/promo-codes').then(({ data }) => setRows(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const create = async (e) => {
    e.preventDefault(); setBusy(true);
    try { await api.post('/admin/promo-codes', { ...f, value: Number(f.value), max_uses: Number(f.max_uses) || 0 }); toast({ title: 'Promo code created' }); setF(EMPTY); load(); }
    catch (ex) { toast({ title: 'Could not create code', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const toggle = async (id) => { await api.post(`/admin/promo-codes/${id}/toggle`); load(); };
  const remove = async (id) => { await api.delete(`/admin/promo-codes/${id}`); load(); };
  const evName = (id) => (id ? (events || []).find((e) => e.id === id)?.title || 'One event' : 'All events');
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-end sm:items-center justify-center sm:p-5" onClick={onClose}>
      <div data-testid="promo-panel" className="bg-white w-full sm:max-w-2xl rounded-t-3xl sm:rounded-3xl p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between"><h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Tag size={18} className="text-[#B4247E]" /> Ticket promo codes</h3>
          <button data-testid="promo-close" onClick={onClose} aria-label="Close" className="w-10 h-10 flex items-center justify-center"><X size={20} /></button></div>
        <form onSubmit={create} className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 mt-4">
          <label className="text-[12px] font-semibold text-[#3B0A2E]">Code<input data-testid="promo-code" required value={f.code} onChange={(e) => setF({ ...f, code: e.target.value.toUpperCase() })} placeholder="EARLYBIRD" className={input} /></label>
          <label className="text-[12px] font-semibold text-[#3B0A2E]">Discount<select data-testid="promo-kind" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={input}><option value="percent">% off</option><option value="amount">$ off</option></select></label>
          <label className="text-[12px] font-semibold text-[#3B0A2E]">{f.kind === 'percent' ? 'Percent' : 'Dollars'}<input data-testid="promo-value" type="number" min="1" step="0.01" required value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} className={input} /></label>
          <label className="text-[12px] font-semibold text-[#3B0A2E] col-span-2 sm:col-span-1">Event<select data-testid="promo-event" value={f.event_id} onChange={(e) => setF({ ...f, event_id: e.target.value })} className={input}><option value="">All events</option>{(events || []).map((e) => <option key={e.id} value={e.id}>{e.title}</option>)}</select></label>
          <label className="text-[12px] font-semibold text-[#3B0A2E]">Use limit (0 = none)<input data-testid="promo-max" type="number" min="0" value={f.max_uses} onChange={(e) => setF({ ...f, max_uses: e.target.value })} className={input} /></label>
          <label className="text-[12px] font-semibold text-[#3B0A2E]">Expires (optional)<input data-testid="promo-expires" type="date" value={f.expires} onChange={(e) => setF({ ...f, expires: e.target.value })} className={input} /></label>
          <button data-testid="promo-create" disabled={busy} className="col-span-2 sm:col-span-3 btn-magenta rounded-full py-2.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">{busy && <Loader2 size={14} className="animate-spin" />} Create code</button>
        </form>
        <div className="mt-5 space-y-2">
          {!rows.length && <p className="text-[13px] text-[#241019]/55">No promo codes yet.</p>}
          {rows.map((r) => (
            <div key={r.id} data-testid={`promo-row-${r.code}`} className="flex items-center gap-3 rounded-2xl border border-[#3B0A2E]/10 px-4 py-3 text-[13.5px]">
              <div className="flex-1 min-w-0"><p className="font-semibold text-[#3B0A2E]">{r.code} <span className="text-[#B4247E]">{r.kind === 'percent' ? `${r.value}% off` : `$${r.value} off`}</span></p>
                <p className="text-[#241019]/55">{evName(r.event_id)} · used {r.uses}{r.max_uses ? ` of ${r.max_uses}` : ''}{r.expires ? ` · expires ${r.expires}` : ''}</p></div>
              <button data-testid={`promo-toggle-${r.code}`} onClick={() => toggle(r.id)} className={`rounded-full px-3 py-1.5 text-[12px] font-semibold ${r.active ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>{r.active ? 'Active' : 'Off'}</button>
              <button data-testid={`promo-delete-${r.code}`} onClick={() => remove(r.id)} aria-label="Delete" className="w-9 h-9 flex items-center justify-center text-red-500"><Trash2 size={15} /></button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
