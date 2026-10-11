import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { Loader2, Ticket, Check, Minus, Plus, MapPin, CalendarDays } from 'lucide-react';
import { api } from '../lib/api';

const money = (n) => `$${Number(n).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

export const TicketPicker = ({ ev, onDone }) => {
  const [qty, setQty] = useState({});
  const [f, setF] = useState({ name: '', email: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const types = ev.ticket_types || [];
  const total = types.reduce((a, t) => a + (qty[t.id] || 0) * t.price, 0);
  const step = (t, d) => setQty({ ...qty, [t.id]: Math.max(0, Math.min(Math.min(t.remaining, 20), (qty[t.id] || 0) + d)) });
  const pay = async (e) => {
    e.preventDefault(); setBusy(true); setErr('');
    try {
      const { data } = await api.post(`/events/${ev.id}/tickets/checkout`, { ...f, items: types.map((t) => ({ type_id: t.id, qty: qty[t.id] || 0 })).filter((i) => i.qty) });
      window.location.href = data.url;
    } catch (ex) { setErr(ex?.response?.data?.detail || 'Could not start checkout.'); setBusy(false); }
  };
  const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E]';
  return (
    <form onSubmit={pay} data-testid="ticket-picker" className="space-y-4">
      {types.map((t) => (
        <div key={t.id} data-testid={`ticket-type-${t.id}`} className="flex items-center gap-3 rounded-2xl border border-[#3B0A2E]/10 px-4 py-3">
          <div className="flex-1 min-w-0">
            <p className="font-semibold text-[#3B0A2E]">{t.name} <span className="text-[#B4247E]">{money(t.price)}</span></p>
            <p className="text-[12.5px] text-[#241019]/55">{t.admits > 1 ? `Admits ${t.admits} · ` : ''}{t.remaining > 0 ? `${t.remaining} left` : 'Sold out'}</p>
          </div>
          <button type="button" data-testid={`ticket-minus-${t.id}`} onClick={() => step(t, -1)} className="w-10 h-10 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center" aria-label="Fewer"><Minus size={15} /></button>
          <span data-testid={`ticket-qty-${t.id}`} className="w-6 text-center font-semibold">{qty[t.id] || 0}</span>
          <button type="button" data-testid={`ticket-plus-${t.id}`} disabled={t.remaining <= (qty[t.id] || 0)} onClick={() => step(t, 1)} className="w-10 h-10 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center disabled:opacity-40" aria-label="More"><Plus size={15} /></button>
        </div>
      ))}
      <input data-testid="ticket-name" required placeholder="Your name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={input} />
      <input data-testid="ticket-email" required type="email" inputMode="email" placeholder="Email for your tickets" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={input} />
      {err && <p data-testid="ticket-error" className="text-[13px] text-red-600">{err}</p>}
      <button data-testid="ticket-pay-btn" disabled={busy || !total} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-50">{busy ? <Loader2 size={16} className="animate-spin" /> : <Ticket size={16} />} {total ? `Pay ${money(total)}` : 'Choose tickets'}</button>
      <p className="text-[12px] text-[#241019]/50 text-center">Secure payment by Stripe. Your QR tickets arrive by email.</p>
    </form>
  );
};

export function TicketSuccess() {
  const [sp] = useSearchParams();
  const [d, setD] = useState(null);
  useEffect(() => {
    const sid = sp.get('session_id'); let n = 0;
    const poll = () => api.get(`/tickets/session/${sid}`).then(({ data }) => { setD(data); if (data.status !== 'paid' && ++n < 10) setTimeout(poll, 2000); }).catch(() => setD({ status: 'error' }));
    poll();
  }, [sp]);
  return (
    <div className="min-h-[70vh] bg-[#F7EFE9] py-16 px-5" data-testid="ticket-success">
      <div className="max-w-md mx-auto bg-white rounded-3xl p-8 text-center border border-[#3B0A2E]/8">
        {!d || d.status === 'pending' ? <><Loader2 className="animate-spin text-[#B4247E] mx-auto" /><p className="mt-4 text-[#241019]/70">Confirming your payment…</p></> : d.status === 'paid' ? (
          <>
            <span className="w-14 h-14 rounded-full bg-emerald-50 text-emerald-600 inline-flex items-center justify-center"><Check size={26} /></span>
            <h1 className="font-serif text-[28px] text-[#3B0A2E] font-semibold mt-4">You're going!</h1>
            <p className="text-[14.5px] text-[#241019]/70 mt-2">Your tickets for <strong>{d.event_title}</strong> were emailed to {d.email}.</p>
            <Link data-testid="ticket-view-link" to={`/tickets/${d.token}`} className="inline-block mt-6 btn-magenta rounded-full px-7 py-3 font-semibold">View my tickets</Link>
          </>
        ) : <p data-testid="ticket-success-error" className="text-[#241019]/70">We couldn't confirm this order. If you were charged, your tickets will arrive by email shortly.</p>}
      </div>
    </div>
  );
}

export default function MyTickets() {
  const { token } = useParams();
  const [d, setD] = useState(null);
  useEffect(() => { api.get(`/tickets/order/${token}`).then(({ data }) => setD(data)).catch(() => setD(false)); }, [token]);
  if (d === null) return <div className="py-24 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!d) return <p className="py-24 text-center text-[#241019]/70" data-testid="tickets-not-found">Tickets not found.</p>;
  return (
    <div className="bg-[#F7EFE9] py-12 px-5 min-h-[70vh]" data-testid="my-tickets">
      <div className="max-w-3xl mx-auto">
        <p className="eyebrow text-[#B4247E]">Tickets for {d.name}</p>
        <h1 className="font-serif text-[30px] sm:text-[36px] text-[#3B0A2E] font-semibold mt-1">{d.event.title}</h1>
        <p className="text-[14px] text-[#241019]/70 mt-2 flex flex-wrap gap-x-5 gap-y-1"><span className="flex items-center gap-1.5"><CalendarDays size={14} /> {d.event.date}{d.event.time ? ` · ${d.event.time}` : ''}</span>{d.event.location && <span className="flex items-center gap-1.5"><MapPin size={14} /> {d.event.location}</span>}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-7">
          {d.tickets.map((t) => (
            <div key={t.code} data-testid={`ticket-${t.seat}`} className="bg-white rounded-3xl p-6 text-center border border-[#3B0A2E]/8">
              <QRCodeSVG value={`CSCT:${t.code}`} size={200} fgColor="#3B0A2E" className="mx-auto" />
              <p className="font-semibold text-[#3B0A2E] mt-3">{t.type} · Seat {t.seat}</p>
              <p className={`text-[12.5px] mt-1 ${t.checked_in_at ? 'text-emerald-700' : 'text-[#241019]/55'}`}>{t.checked_in_at ? 'Checked in' : 'Show at the door'}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
