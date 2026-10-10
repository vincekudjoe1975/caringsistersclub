import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, X, Send, LogIn, UserMinus, Clock } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const fmt = (iso) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });

export const countdown = (iso, now) => {
  const ms = new Date(iso).getTime() - now;
  if (ms <= 0) return 'expired';
  const h = Math.floor(ms / 36e5), m = Math.floor((ms % 36e5) / 6e4);
  return `${h}h ${m}m left`;
};

const STATUS = {
  waiting: ['Waiting', '#eef1f5', '#53657d'], open: ['Offer open', '#fdf3e1', '#8a6a2c'],
  expired: ['Offer expired', '#f5e9ec', '#9b3b4f'],
};

function Row({ it, now, onAct, busy }) {
  const [label, bg, color] = STATUS[it.offer_status] || STATUS.waiting;
  const btn = 'p-2 rounded-full hover:bg-[#faf2f7] disabled:opacity-40';
  return (
    <tr className="border-t border-[#3B0A2E]/8" data-testid="waitlist-row">
      <td className="px-3 py-2.5 font-bold text-[#B4247E]" data-testid="waitlist-position">#{it.position}</td>
      <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E]">{it.name}</p><p className="text-[11.5px] text-[#241019]/55">{it.email}</p></td>
      <td className="px-3 py-2.5 text-[#241019]/65">{fmt(it.joined)}</td>
      <td className="px-3 py-2.5">
        <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full" style={{ background: bg, color }} data-testid="waitlist-offer-status">{label}</span>
        {it.offer_expires && <p className="text-[11px] text-[#8a6a2c] mt-1 flex items-center gap-1" data-testid="waitlist-countdown"><Clock size={11} /> {countdown(it.offer_expires, now)}</p>}
      </td>
      <td className="px-3 py-2.5 text-right whitespace-nowrap">
        <button disabled={busy} onClick={() => onAct(it, 'offer')} title="Send offer now" data-testid="waitlist-offer-btn" className={`${btn} text-[#8a6a2c]`}><Send size={15} /></button>
        <button disabled={busy} onClick={() => onAct(it, 'move-in')} title="Move in" data-testid="waitlist-movein-btn" className={`${btn} text-[#3c7a2f]`}><LogIn size={15} /></button>
        <button disabled={busy} onClick={() => onAct(it, 'remove')} title="Remove" data-testid="waitlist-remove-btn" className={`${btn} text-red-500`}><UserMinus size={15} /></button>
      </td>
    </tr>
  );
}

const CONFIRM = { offer: 'Email a 48-hour claim link to', 'move-in': 'Move into the program (and email "You\'re in!")', remove: 'Remove from the waitlist' };

export const WaitlistPanel = ({ program, onClose }) => {
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [now, setNow] = useState(Date.now());
  const load = useCallback(() => api.get(`/admin/programs/${program.id}/waitlist`).then(({ data }) => setD(data)).catch(() => setD({ items: [] })), [program.id]);
  useEffect(() => { load(); const t = setInterval(() => setNow(Date.now()), 30000); return () => clearInterval(t); }, [load]);
  const act = async (it, action) => {
    if (!window.confirm(`${CONFIRM[action]} ${it.name}?`)) return;
    setBusy(true);
    try { await api.post(`/admin/waitlist/${it.id}/${action}`); toast({ title: action === 'offer' ? 'Offer sent' : action === 'move-in' ? 'Moved into program' : 'Removed from waitlist' }); load(); }
    catch (err) { toast({ title: 'Action failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} data-testid="waitlist-panel" className="bg-white rounded-2xl max-w-3xl w-full max-h-[88vh] overflow-y-auto p-7">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Waitlist · {program.title}</h3>
            {d && <p className="text-[12.5px] text-[#241019]/60" data-testid="waitlist-summary">{d.items.length} waiting{d.capacity ? ` · ${d.seats_left} of ${d.capacity} seats free` : ''} · mode: {d.mode}</p>}
          </div>
          <button onClick={onClose} data-testid="waitlist-close-btn" className="p-2 text-[#3B0A2E]"><X size={18} /></button>
        </div>
        {!d ? <Loader2 className="animate-spin text-[#B4247E] mx-auto" /> : d.items.length === 0 ? <p className="text-[13.5px] text-[#241019]/55 text-center py-8" data-testid="waitlist-empty">No one is on the waitlist.</p> : (
          <table className="w-full text-left text-[13px]"><thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-3 py-2">#</th><th className="px-3 py-2">Sister</th><th className="px-3 py-2">Joined</th><th className="px-3 py-2">Offer</th><th /></tr></thead>
            <tbody>{d.items.map((it) => <Row key={it.id} it={it} now={now} onAct={act} busy={busy} />)}</tbody></table>
        )}
      </div>
    </div>
  );
};
