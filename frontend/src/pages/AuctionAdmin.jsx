import React, { useCallback, useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { ArrowLeft, Plus, Trash2, Download, Gavel } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E]';
const money = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
const EMPTY = { title: '', description: '', value: '', start_bid: '', min_raise: 10, photo: '' };

export default function AuctionAdmin() {
  const { eid } = useParams();
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [f, setF] = useState(EMPTY);
  const [closes, setCloses] = useState('');
  const load = useCallback(() => api.get(`/admin/events/${eid}/auction`).then(({ data }) => { setD(data); setCloses(data.closes_local || ''); }).catch(() => setD(false)), [eid]);
  useEffect(() => { load(); const t = setInterval(load, 10000); return () => clearInterval(t); }, [load]);
  const err = (ex) => toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' });
  const upload = async (file) => { const fd = new FormData(); fd.append('file', file); try { const { data } = await api.post('/admin/auction/photo', fd); setF((x) => ({ ...x, photo: data.url })); } catch (ex) { err(ex); } };
  const add = (e) => { e.preventDefault(); api.post(`/admin/events/${eid}/auction/items`, { ...f, value: Number(f.value) || 0, start_bid: Number(f.start_bid), min_raise: Number(f.min_raise) }).then(() => { setF(EMPTY); load(); }).catch(err); };
  const csv = async () => { const res = await api.get(`/admin/events/${eid}/auction.csv`, { responseType: 'blob' }); const u = URL.createObjectURL(res.data); const a = document.createElement('a'); a.href = u; a.download = 'auction.csv'; a.click(); };
  if (d === null) return null;
  if (!d) return <p className="p-10 text-center">Event not found.</p>;
  return (
    <div className="min-h-screen bg-[#F7EFE9]" data-testid="auction-admin">
      <div className="csc-hero-gradient text-[#F7EFE9] px-5 py-6">
        <Link to="/admin?tab=events" className="text-[13px] flex items-center gap-1 text-[#F7EFE9]/75"><ArrowLeft size={14} /> Admin</Link>
        <h1 className="font-serif text-[26px] font-semibold mt-2 flex items-center gap-2"><Gavel size={22} /> Silent auction: {d.title}</h1>
        <p data-testid="auction-admin-summary" className="text-[14px] text-[#F7EFE9]/80 mt-1">{d.state === 'closed' ? 'Closed' : d.state === 'open' ? 'Open' : 'Not open yet'} · {d.items.length} items · {d.bidders} bidders · {money(d.total_bids)} in high bids</p>
        <div className="flex flex-wrap items-end gap-2 mt-4">
          {d.state !== 'closed' && <label className="text-[12.5px]">Bidding closes (Eastern)<input data-testid="auction-closes" type="datetime-local" value={closes} onChange={(e) => setCloses(e.target.value)} className="block mt-1 rounded-full px-4 py-2 text-[#241019]" /></label>}
          {d.state !== 'closed' && <button data-testid="auction-closes-save" onClick={() => api.put(`/admin/events/${eid}/auction`, { closes_at: closes }).then(({ data }) => { setD(data); toast({ title: 'Auction is open for bids' }); }).catch(err)} className="rounded-full px-5 py-2.5 font-semibold bg-[#CBA24B] text-[#3B0A2E]">{d.state === 'open' ? 'Update time' : 'Open bidding'}</button>}
          {d.state === 'open' && <button data-testid="auction-close-now" onClick={() => window.confirm('Close bidding now and email the winners?') && api.post(`/admin/events/${eid}/auction/close`).then(load).catch(err)} className="rounded-full px-5 py-2.5 font-semibold border border-white/25">Close now</button>}
          <a data-testid="auction-public-link" href={`/auction/${eid}`} target="_blank" rel="noopener noreferrer" className="rounded-full px-5 py-2.5 font-semibold border border-white/25">Guest page</a>
          <button data-testid="auction-csv" onClick={csv} className="rounded-full px-5 py-2.5 font-semibold border border-white/25 flex items-center gap-1.5"><Download size={14} /> CSV</button>
        </div>
      </div>
      <div className="px-5 py-5 max-w-5xl mx-auto grid lg:grid-cols-[340px_1fr] gap-5">
        {d.state !== 'closed' && (
          <form onSubmit={add} data-testid="auction-item-form" className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8 space-y-2.5 self-start">
            <p className="font-semibold text-[#3B0A2E]">Add an item</p>
            <input data-testid="ai-title" required placeholder="Title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={input} />
            <textarea data-testid="ai-desc" rows={2} placeholder="Description" value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} className={input} />
            <div className="grid grid-cols-3 gap-2">
              <input data-testid="ai-value" type="number" placeholder="Value $" value={f.value} onChange={(e) => setF({ ...f, value: e.target.value })} className={input} />
              <input data-testid="ai-start" type="number" required placeholder="Start $" value={f.start_bid} onChange={(e) => setF({ ...f, start_bid: e.target.value })} className={input} />
              <input data-testid="ai-raise" type="number" required placeholder="Raise $" value={f.min_raise} onChange={(e) => setF({ ...f, min_raise: e.target.value })} className={input} />
            </div>
            <label className="block text-[13px] text-[#B4247E] font-semibold cursor-pointer">{f.photo ? 'Photo added ✓ (change)' : 'Add a photo'}<input data-testid="ai-photo" type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} /></label>
            <button data-testid="ai-add" className="btn-magenta rounded-full w-full py-2.5 font-semibold flex items-center justify-center gap-1.5"><Plus size={15} /> Add item</button>
          </form>
        )}
        <div className="space-y-2.5">
          {!d.items.length && <p className="text-[#241019]/55">No items yet.</p>}
          {d.items.map((i) => (
            <div key={i.id} data-testid={`ai-row-${i.id}`} className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8 flex gap-3">
              {i.photo && <img src={mediaSrc(i.photo)} alt="" className="w-16 h-16 rounded-xl object-cover" />}
              <div className="flex-1 min-w-0 text-[13.5px]">
                <p className="font-semibold text-[#3B0A2E]">{i.title}</p>
                <p className="text-[#241019]/60">{i.high_bid ? `High bid ${money(i.high_bid)} (${i.bid_count} bids)` : `Starts at ${money(i.start_bid)}`}{i.high_bidder ? ` · ${i.high_bidder.name}, ${i.high_bidder.phone}` : ''}</p>
                {i.win && <p data-testid={`ai-win-${i.id}`} className={`font-semibold ${i.win.status === 'paid' ? 'text-emerald-700' : 'text-amber-700'}`}>Winner {i.win.name}: {i.win.status}</p>}
              </div>
              {!i.bid_count && d.state !== 'closed' && <button data-testid={`ai-del-${i.id}`} onClick={() => api.delete(`/admin/events/${eid}/auction/items/${i.id}`).then(load).catch(err)} aria-label="Delete" className="w-9 h-9 flex items-center justify-center text-red-500"><Trash2 size={15} /></button>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
