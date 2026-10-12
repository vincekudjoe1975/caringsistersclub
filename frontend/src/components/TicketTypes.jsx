import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { Plus, Trash2, Loader2, X, QrCode } from 'lucide-react';
import { api } from '../lib/api';
import { GalaExtras } from './GalaExtras';

const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

export const TicketTypesPanel = ({ ev, onClose, onSaved, toast }) => {
  const [rows, setRows] = useState(() => (ev.ticket_types || []).map((t) => ({ ...t })));
  const [busy, setBusy] = useState(false);
  const [goal, setGoal] = useState(ev.gala_goal || '');
  const saveGoal = async () => {
    try { await api.put(`/admin/events/${ev.id}/gala`, { goal: Number(goal) || 0 }); toast({ title: 'Gala goal saved' }); } catch (ex) { toast({ title: 'Could not save goal', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const set = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const save = async () => {
    setBusy(true);
    try {
      await api.put(`/admin/events/${ev.id}/tickets`, { ticket_types: rows.map((r) => ({ id: r.id || '', name: r.name, price: Number(r.price), qty: Number(r.qty), admits: Number(r.admits) || 1 })) });
      toast({ title: rows.length ? 'Tickets saved' : 'Ticket sales turned off' }); onSaved();
    } catch (ex) { toast({ title: 'Could not save tickets', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/40 flex items-end sm:items-center justify-center p-0 sm:p-5" onClick={onClose}>
      <div data-testid="ticket-types-panel" className="bg-white w-full sm:max-w-2xl rounded-t-3xl sm:rounded-3xl p-6 max-h-[90vh] overflow-y-auto" onClick={(e) => e.stopPropagation()}>
        <div className="flex items-start justify-between gap-3">
          <div><h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Tickets: {ev.title}</h3><p className="text-[13px] text-[#241019]/60">Add paid ticket types. Leave empty for a free RSVP event.</p></div>
          <button data-testid="ticket-types-close" onClick={onClose} aria-label="Close" className="w-10 h-10 flex items-center justify-center"><X size={20} /></button>
        </div>
        <div className="space-y-3 mt-5">
          {rows.map((r, i) => (
            <div key={i} data-testid={`ticket-type-row-${i}`} className="grid grid-cols-2 sm:grid-cols-[1.6fr_1fr_1fr_1fr_auto] gap-2 items-end">
              <label className="col-span-2 sm:col-span-1 text-[12px] font-semibold text-[#3B0A2E]">Name<input data-testid={`tt-name-${i}`} value={r.name} onChange={(e) => set(i, 'name', e.target.value)} placeholder="General" className={input} /></label>
              <label className="text-[12px] font-semibold text-[#3B0A2E]">Price $<input data-testid={`tt-price-${i}`} type="number" min="1" value={r.price} onChange={(e) => set(i, 'price', e.target.value)} className={input} /></label>
              <label className="text-[12px] font-semibold text-[#3B0A2E]">Quantity<input data-testid={`tt-qty-${i}`} type="number" min="1" value={r.qty} onChange={(e) => set(i, 'qty', e.target.value)} className={input} /></label>
              <label className="text-[12px] font-semibold text-[#3B0A2E]">Seats each<input data-testid={`tt-admits-${i}`} type="number" min="1" max="20" value={r.admits} onChange={(e) => set(i, 'admits', e.target.value)} className={input} /></label>
              <button data-testid={`tt-remove-${i}`} onClick={() => setRows(rows.filter((_, j) => j !== i))} aria-label="Remove" className="w-10 h-10 flex items-center justify-center text-red-500"><Trash2 size={16} /></button>
              {r.remaining !== undefined && <p className="col-span-2 sm:col-span-5 text-[12px] text-[#241019]/50 -mt-1">{r.qty - r.remaining} sold</p>}
            </div>
          ))}
          <button data-testid="tt-add" onClick={() => setRows([...rows, { name: '', price: 75, qty: 100, admits: 1 }])} className="text-[13.5px] font-semibold text-[#B4247E] flex items-center gap-1.5"><Plus size={15} /> Add ticket type</button>
        </div>
        <div data-testid="gala-goal-box" className="mt-6 pt-4 border-t border-[#3B0A2E]/10 flex flex-wrap items-end gap-2">
          <label className="text-[12px] font-semibold text-[#3B0A2E]">Live giving goal $<input data-testid="gala-goal-input" type="number" min="0" value={goal} onChange={(e) => setGoal(e.target.value)} className={`${input} w-36`} /></label>
          <button data-testid="gala-goal-save" onClick={saveGoal} className="rounded-full px-4 py-2.5 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] text-[13.5px]">Save goal</button>
          <a data-testid="gala-screen-link" href={`/gala/${ev.id}`} target="_blank" rel="noopener noreferrer" className="rounded-full px-4 py-2.5 font-semibold text-[13.5px] text-[#B4247E] underline">Open big-screen giving page</a>
        </div>
        <GalaExtras ev={ev} toast={toast} />
        <div className="flex flex-wrap items-center gap-3 mt-6">
          <Link data-testid="ticket-door-link" to={`/admin/tickets/${ev.id}`} className="rounded-full px-5 py-2.5 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5"><QrCode size={15} /> Door check-in & sales</Link>
          <button data-testid="ticket-types-save" disabled={busy} onClick={save} className="btn-magenta rounded-full px-6 py-2.5 font-semibold ml-auto flex items-center gap-2 disabled:opacity-60">{busy && <Loader2 size={14} className="animate-spin" />} Save tickets</button>
        </div>
      </div>
    </div>
  );
};
