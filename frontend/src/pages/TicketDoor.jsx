import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { QrCode, Download, Undo2, ArrowLeft, Search, Loader2, LayoutGrid } from 'lucide-react';
import { api } from '../lib/api';
import { Scanner } from './CheckIn';

export default function TicketDoor() {
  const { eid } = useParams();
  const [r, setR] = useState(null);
  const [scan, setScan] = useState(false);
  const [flash, setFlash] = useState(null);
  const [q, setQ] = useState('');
  const load = useCallback(() => api.get(`/admin/events/${eid}/tickets/report`).then(({ data }) => setR(data)).catch(() => setR(false)), [eid]);
  useEffect(() => { load(); }, [load]);
  const checkin = useCallback(async (code) => {
    try {
      const { data } = await api.post(`/admin/events/${eid}/tickets/checkin`, { code });
      setFlash({ ok: data.ok, text: data.ok ? `Welcome, ${data.holder}! ${data.type} · seat ${data.seat}` : `Already checked in: ${data.holder} (seat ${data.seat})` });
      load();
    } catch (ex) { setFlash({ ok: false, text: ex?.response?.data?.detail || 'Ticket not valid' }); }
    setTimeout(() => setFlash(null), 3500);
  }, [eid, load]);
  const undo = async (code) => { await api.post(`/admin/events/${eid}/tickets/undo`, { code }); load(); };
  const csv = async () => {
    const res = await api.get(`/admin/events/${eid}/tickets.csv`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data); const a = document.createElement('a'); a.href = url; a.download = `tickets-${eid.slice(0, 8)}.csv`; a.click(); URL.revokeObjectURL(url);
  };
  if (r === null) return <div className="py-24 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!r) return <p className="p-10 text-center">Event not found. <Link to="/admin" className="underline">Back to admin</Link></p>;
  const guests = r.guests.filter((g) => g.holder.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="min-h-screen bg-[#F7EFE9]" data-testid="ticket-door">
      <div className="csc-hero-gradient text-[#F7EFE9] px-5 py-6">
        <Link to="/admin?tab=events" className="text-[13px] flex items-center gap-1 text-[#F7EFE9]/75"><ArrowLeft size={14} /> Admin</Link>
        <h1 className="font-serif text-[26px] font-semibold mt-2">{r.event.title}</h1>
        <p data-testid="ticket-door-summary" className="text-[14px] text-[#F7EFE9]/80 mt-1">{r.checked_in} of {r.seats} guests checked in · {r.orders} orders · ${r.revenue.toLocaleString('en-US')} in ticket sales</p>
        <div className="flex flex-wrap gap-2 mt-4">
          <button data-testid="ticket-door-scan" onClick={() => setScan(true)} className="rounded-full px-6 py-3 font-semibold bg-[#CBA24B] text-[#3B0A2E] flex items-center gap-2"><QrCode size={17} /> Scan tickets</button>
          <Link data-testid="ticket-door-seating" to={`/admin/tickets/${eid}/seating`} className="rounded-full px-5 py-3 font-semibold border border-white/25 flex items-center gap-2"><LayoutGrid size={15} /> Seating</Link>
          <button data-testid="ticket-door-csv" onClick={csv} className="rounded-full px-5 py-3 font-semibold border border-white/25 flex items-center gap-2"><Download size={15} /> CSV</button>
        </div>
      </div>
      {flash && <div data-testid="ticket-door-flash" className={`mx-5 mt-4 rounded-2xl px-5 py-4 font-semibold text-[15px] ${flash.ok ? 'bg-emerald-600 text-white' : 'bg-amber-500 text-white'}`}>{flash.text}</div>}
      <div className="px-5 py-5 max-w-3xl mx-auto space-y-5">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3" data-testid="ticket-door-types">
          {r.types.map((t) => (
            <div key={t.id} className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8">
              <p className="font-semibold text-[#3B0A2E]">{t.name}</p>
              <p className="text-[13px] text-[#241019]/60">{t.sold} of {t.qty} sold · ${t.revenue.toLocaleString('en-US')}</p>
            </div>
          ))}
        </div>
        <label className="relative block"><Search size={15} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#241019]/40" />
          <input data-testid="ticket-door-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search guest name" className="w-full rounded-full border border-[#3B0A2E]/15 pl-10 pr-4 py-3 bg-white text-[14px]" /></label>
        <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden">
          {!guests.length ? <p className="p-6 text-center text-[#241019]/55">No tickets sold yet.</p> : guests.map((g) => (
            <div key={g.code} data-testid={`ticket-guest-${g.code}`} className={`flex items-center gap-3 px-4 py-3 border-b border-[#3B0A2E]/8 ${g.checked_in_at ? 'bg-green-50' : ''}`}>
              <div className="flex-1 min-w-0"><p className="font-semibold text-[#3B0A2E] truncate">{g.holder}</p><p className="text-[12.5px] text-[#241019]/55">{g.type} · seat {g.seat}{g.checked_in_at ? ' · checked in' : ''}</p></div>
              {g.checked_in_at
                ? <button data-testid={`ticket-undo-${g.code}`} onClick={() => undo(g.code)} aria-label="Undo" className="w-10 h-10 flex items-center justify-center text-[#241019]/50"><Undo2 size={17} /></button>
                : <button data-testid={`ticket-checkin-${g.code}`} onClick={() => checkin(g.code)} className="btn-magenta rounded-full px-4 py-2 text-[13.5px] font-semibold">Check in</button>}
            </div>
          ))}
        </div>
      </div>
      {scan && <Scanner onCode={checkin} onClose={() => setScan(false)} prompt="Point the camera at the guest's ticket QR code" />}
    </div>
  );
}
