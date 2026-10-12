import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Printer, Wand2, Loader2, Users } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

export default function Seating() {
  const { eid } = useParams();
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [cfg, setCfg] = useState({ tables: 10, seats: 8 });
  const [pick, setPick] = useState(null);
  const [print, setPrint] = useState('');
  const apply = (data) => { setD(data); if (data.seating.tables) setCfg({ tables: data.seating.tables, seats: data.seating.seats }); };
  const load = useCallback(() => api.get(`/admin/events/${eid}/seating`).then(({ data }) => apply(data)).catch(() => setD(false)), [eid]);
  useEffect(() => { load(); }, [load]);
  const err = (ex) => toast({ title: 'Could not update', description: ex?.response?.data?.detail, variant: 'destructive' });
  const saveCfg = () => api.put(`/admin/events/${eid}/seating`, { ...cfg, tables: Number(cfg.tables), seats: Number(cfg.seats), names: d?.seating?.names || {} }).then(({ data }) => { apply(data); toast({ title: 'Tables saved' }); }).catch(err);
  const auto = () => api.post(`/admin/events/${eid}/seating/auto`).then(({ data }) => { apply(data); toast({ title: `Seated ${data.seated} guest${data.seated === 1 ? '' : 's'}` }); }).catch(err);
  const assign = (table) => { if (!pick) return; api.post(`/admin/events/${eid}/seating/assign`, { group: pick, table }).then(({ data }) => { apply(data); setPick(null); }).catch(err); };
  const doPrint = (mode) => { setPrint(mode); setTimeout(() => { window.print(); setPrint(''); }, 150); };
  if (d === null) return <div className="py-24 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!d) return <p className="p-10 text-center">Event not found.</p>;
  const tables = Array.from({ length: d.seating.tables || 0 }, (_, i) => i + 1);
  const at = (t) => d.groups.filter((g) => g.table === t);
  const unseated = d.groups.filter((g) => !g.table);
  const used = (t) => at(t).reduce((a, g) => a + g.size, 0);
  const cards = d.groups.flatMap((g) => g.names.map((n, i) => ({ k: `${g.group}${i}`, n, t: g.table }))).filter((c) => c.t).sort((a, b) => a.t - b.t);
  if (print === 'cards') return (
    <div data-testid="place-cards" className="grid grid-cols-2 gap-0 bg-white">
      {cards.map((c) => <div key={c.k} className="h-[2.6in] border border-dashed border-gray-300 flex flex-col items-center justify-center text-center break-inside-avoid"><p className="font-serif text-[28px] text-[#3B0A2E]">{c.n}</p><p className="mt-2 text-[16px] tracking-[0.2em] uppercase text-[#B4247E]">Table {c.t}</p><p className="mt-4 text-[11px] text-gray-500">{d.event.title}</p></div>)}
    </div>
  );
  if (print === 'chart') return (
    <div data-testid="seating-chart-print" className="bg-white p-8">
      <h1 className="font-serif text-[28px] text-[#3B0A2E]">{d.event.title}: Seating</h1><p className="text-gray-600 mb-6">{d.event.date}{d.event.location ? ` · ${d.event.location}` : ''}</p>
      <div className="grid grid-cols-3 gap-4">{tables.map((t) => <div key={t} className="border border-gray-300 rounded-lg p-3 break-inside-avoid"><p className="font-bold text-[#3B0A2E]">Table {t}</p>{at(t).flatMap((g) => g.names).map((n, i) => <p key={i} className="text-[13px]">{n}</p>)}</div>)}</div>
    </div>
  );
  return (
    <div className="min-h-screen bg-[#F7EFE9]" data-testid="seating-page">
      <div className="csc-hero-gradient text-[#F7EFE9] px-5 py-6">
        <Link to={`/admin/tickets/${eid}`} className="text-[13px] flex items-center gap-1 text-[#F7EFE9]/75"><ArrowLeft size={14} /> Door & sales</Link>
        <h1 className="font-serif text-[26px] font-semibold mt-2">Seating: {d.event.title}</h1>
        <div className="flex flex-wrap items-end gap-3 mt-4">
          <label className="text-[12.5px]">Tables<input data-testid="seating-tables" type="number" min="1" max="200" value={cfg.tables} onChange={(e) => setCfg({ ...cfg, tables: e.target.value })} className="block w-24 mt-1 rounded-full px-4 py-2 text-[#241019]" /></label>
          <label className="text-[12.5px]">Seats per table<input data-testid="seating-seats" type="number" min="1" max="30" value={cfg.seats} onChange={(e) => setCfg({ ...cfg, seats: e.target.value })} className="block w-24 mt-1 rounded-full px-4 py-2 text-[#241019]" /></label>
          <button data-testid="seating-save" onClick={saveCfg} className="rounded-full px-5 py-2.5 font-semibold bg-[#CBA24B] text-[#3B0A2E]">Save tables</button>
          {tables.length > 0 && <button data-testid="seating-auto" onClick={auto} className="rounded-full px-5 py-2.5 font-semibold border border-white/25 flex items-center gap-1.5"><Wand2 size={15} /> Auto-seat</button>}
          {tables.length > 0 && <button data-testid="seating-print-chart" onClick={() => doPrint('chart')} className="rounded-full px-5 py-2.5 font-semibold border border-white/25 flex items-center gap-1.5"><Printer size={15} /> Chart</button>}
          {tables.length > 0 && <button data-testid="seating-print-cards" onClick={() => doPrint('cards')} className="rounded-full px-5 py-2.5 font-semibold border border-white/25 flex items-center gap-1.5"><Printer size={15} /> Place cards</button>}
        </div>
      </div>
      <div className="px-5 py-5 max-w-6xl mx-auto grid lg:grid-cols-[300px_1fr] gap-5">
        <div className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8 self-start" data-testid="seating-unseated">
          <p className="font-semibold text-[#3B0A2E] mb-2">Not seated ({unseated.reduce((a, g) => a + g.size, 0)})</p>
          {pick && <p className="text-[12.5px] text-[#B4247E] font-semibold mb-2">Now tap a table to seat them</p>}
          {!unseated.length ? <p className="text-[13px] text-[#241019]/55">Everyone has a seat.</p> : unseated.map((g) => (
            <button key={g.group} data-testid={`seat-guest-${g.group}`} onClick={() => setPick(pick === g.group ? null : g.group)} className={`w-full text-left rounded-xl px-3 py-2.5 mb-1.5 text-[13.5px] transition-colors ${pick === g.group ? 'bg-[#3B0A2E] text-white' : 'bg-[#faf2f7] text-[#3B0A2E] hover:bg-[#f2e3ec]'}`}>
              <span className="font-semibold">{g.holder}</span> <span className="opacity-70">· {g.type}{g.size > 1 ? ` · ${g.size} seats` : ''}</span>
            </button>
          ))}
        </div>
        {!tables.length ? <p className="text-[#241019]/60">Set the number of tables and seats, then tap Save tables.</p> : (
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
            {tables.map((t) => (
              <div key={t} data-testid={`seat-table-${t}`} onClick={() => assign(t)} className={`bg-white rounded-2xl p-4 border-2 transition-colors ${pick ? 'cursor-pointer border-[#B4247E]/40 hover:border-[#B4247E]' : 'border-transparent'}`}>
                <p className="font-semibold text-[#3B0A2E] flex items-center gap-2">Table {t}<span className={`ml-auto text-[12px] font-semibold flex items-center gap-1 ${used(t) >= d.seating.seats ? 'text-red-600' : 'text-[#241019]/55'}`}><Users size={12} /> {used(t)}/{d.seating.seats}</span></p>
                {at(t).map((g) => (
                  <div key={g.group} className="flex items-center gap-2 mt-1.5 text-[13px]">
                    <span className="flex-1 min-w-0 truncate">{g.holder}{g.size > 1 ? ` (${g.size})` : ''}</span>
                    <button data-testid={`seat-unassign-${g.group}`} onClick={(e) => { e.stopPropagation(); api.post(`/admin/events/${eid}/seating/assign`, { group: g.group, table: null }).then(({ data }) => apply(data)); }} className="text-[12px] text-[#241019]/45 hover:text-red-600">remove</button>
                  </div>
                ))}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
