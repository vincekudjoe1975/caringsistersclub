import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Plus, Undo2, Check, MonitorPlay } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const LEVELS = [1000, 500, 250, 100];
const fmt = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

export default function EmceeControl() {
  const { eid } = useParams();
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [custom, setCustom] = useState('');
  const [who, setWho] = useState({ name: '', email: '', number: '' });
  const load = useCallback(() => api.get(`/admin/events/${eid}/paddle`).then(({ data }) => setD(data)).catch(() => setD(false)), [eid]);
  useEffect(() => { load(); }, [load]);
  const err = (ex) => toast({ title: 'Could not update', description: ex?.response?.data?.detail, variant: 'destructive' });
  const setLevel = (level) => api.put(`/admin/events/${eid}/paddle`, { level }).then(({ data }) => setD(data)).catch(err);
  const pledge = () => api.post(`/admin/events/${eid}/paddle/pledge`, { level: d.level, ...who }).then(({ data }) => { setD(data); setWho({ name: '', email: '', number: '' }); }).catch(err);
  if (d === null) return null;
  if (!d) return <p className="p-10 text-center">Event not found.</p>;
  const pill = (on) => `rounded-2xl py-4 text-[20px] font-serif font-bold transition-colors ${on ? 'bg-[#CBA24B] text-[#3B0A2E]' : 'bg-white/10 text-[#F7EFE9] border border-white/20'}`;
  return (
    <div className="min-h-screen csc-hero-gradient text-[#F7EFE9] px-5 py-6" data-testid="emcee-control">
      <Link to="/admin?tab=events" className="text-[13px] flex items-center gap-1 text-[#F7EFE9]/75"><ArrowLeft size={14} /> Admin</Link>
      <div className="flex items-center gap-3 mt-2"><h1 className="font-serif text-[24px] font-semibold flex-1">Paddle raise: {d.title}</h1>
        <a data-testid="emcee-open-screen" href={`/gala/${eid}`} target="_blank" rel="noopener noreferrer" className="rounded-full px-4 py-2 border border-white/25 text-[13px] flex items-center gap-1.5"><MonitorPlay size={14} /> Screen</a></div>
      <p data-testid="emcee-total" className="text-[15px] text-[#F7EFE9]/80 mt-1">Paddle total {fmt(d.total)} · {d.pledges.length} paddles</p>
      <p className="text-[13px] uppercase tracking-[0.2em] text-[#CBA24B] mt-6 mb-2">Show on screen</p>
      <div className="grid grid-cols-2 gap-2.5">
        {LEVELS.map((l) => <button key={l} data-testid={`emcee-level-${l}`} onClick={() => setLevel(l)} className={pill(d.level === l)}>{fmt(l)}</button>)}
      </div>
      <div className="flex gap-2 mt-2.5">
        <input data-testid="emcee-custom" type="number" min="1" placeholder="Custom $" value={custom} onChange={(e) => setCustom(e.target.value)} className="flex-1 min-w-0 rounded-2xl px-4 py-3 text-[#241019]" />
        <button data-testid="emcee-custom-set" disabled={!custom} onClick={() => setLevel(Number(custom))} className="rounded-2xl px-5 bg-white/15 font-semibold disabled:opacity-40">Show</button>
        <button data-testid="emcee-clear" onClick={() => setLevel(null)} className="rounded-2xl px-4 border border-white/25 text-[13px]">Hide</button>
      </div>
      {d.level && (
        <div className="mt-6 bg-white/10 rounded-3xl p-4 border border-white/15">
          <p className="font-semibold">Paddles at {fmt(d.level)}</p>
          <div className="grid grid-cols-3 gap-2 mt-2">
            <input data-testid="emcee-number" placeholder="Paddle #" value={who.number} onChange={(e) => setWho({ ...who, number: e.target.value })} className="rounded-xl px-3 py-2.5 text-[#241019] text-[14px]" />
            <input data-testid="emcee-name" placeholder="Name" value={who.name} onChange={(e) => setWho({ ...who, name: e.target.value })} className="col-span-2 rounded-xl px-3 py-2.5 text-[#241019] text-[14px]" />
            <input data-testid="emcee-email" type="email" placeholder="Email (for thank-you)" value={who.email} onChange={(e) => setWho({ ...who, email: e.target.value })} className="col-span-3 rounded-xl px-3 py-2.5 text-[#241019] text-[14px]" />
          </div>
          <button data-testid="emcee-plus" onClick={pledge} className="mt-3 w-full rounded-2xl py-5 bg-[#CBA24B] text-[#3B0A2E] font-bold text-[22px] flex items-center justify-center gap-2"><Plus size={24} /> 1 paddle at {fmt(d.level)}</button>
        </div>
      )}
      <div className="mt-6 space-y-1.5" data-testid="emcee-tally">{d.tally.map((t) => <p key={t.level} className="flex justify-between text-[15px]"><span>{fmt(t.level)}</span><span className="font-semibold">{t.count} × = {fmt(t.level * t.count)}</span></p>)}</div>
      <p className="text-[13px] uppercase tracking-[0.2em] text-[#CBA24B] mt-6 mb-2">Pledges to collect</p>
      <div className="bg-white rounded-2xl text-[#241019] divide-y divide-[#3B0A2E]/8">
        {!d.pledges.length && <p className="p-4 text-[13.5px] text-[#241019]/55">No paddles yet.</p>}
        {d.pledges.map((p) => (
          <div key={p.id} data-testid={`pledge-${p.id}`} className="flex items-center gap-3 px-4 py-3 text-[14px]">
            <div className="flex-1 min-w-0"><p className="font-semibold text-[#3B0A2E] truncate">{fmt(p.level)} · {p.name || 'Guest'}{p.number ? ` (#${p.number})` : ''}</p><p className="text-[12.5px] text-[#241019]/55 truncate">{p.email || 'no email'}</p></div>
            <button data-testid={`pledge-collected-${p.id}`} onClick={() => api.post(`/admin/events/${eid}/paddle/pledge/${p.id}/collected`).then(({ data }) => setD(data))} className={`rounded-full px-3 py-1.5 text-[12px] font-semibold flex items-center gap-1 ${p.collected ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'}`}>{p.collected ? <><Check size={12} /> Paid</> : 'Unpaid'}</button>
            <button data-testid={`pledge-undo-${p.id}`} onClick={() => api.delete(`/admin/events/${eid}/paddle/pledge/${p.id}`).then(({ data }) => setD(data))} aria-label="Undo" className="w-9 h-9 flex items-center justify-center text-[#241019]/45"><Undo2 size={15} /></button>
          </div>
        ))}
      </div>
    </div>
  );
}
