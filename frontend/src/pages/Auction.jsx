import React, { useCallback, useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Gavel, Loader2, Check, Trophy } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';

const money = (n) => `$${Number(n || 0).toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;
const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E]';

const Item = ({ i, eid, token, onBid }) => {
  const [amt, setAmt] = useState('');
  const [msg, setMsg] = useState('');
  const bid = async () => {
    setMsg('');
    try { await api.post(`/auction/${eid}/items/${i.id}/bid`, { token, amount: Number(amt || i.next_min) }); setAmt(''); setMsg("You're the highest bidder!"); onBid(); }
    catch (ex) { setMsg(ex?.response?.data?.detail || 'Bid failed'); onBid(); }
  };
  return (
    <div data-testid={`auction-item-${i.id}`} className="bg-white rounded-3xl overflow-hidden border border-[#3B0A2E]/8">
      {i.photo && <img src={mediaSrc(i.photo)} alt={i.title} loading="lazy" className="w-full aspect-[4/3] object-cover" />}
      <div className="p-5">
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold">{i.title}</p>
        {i.description && <p className="text-[13.5px] text-[#241019]/65 mt-1">{i.description}</p>}
        <p className="text-[13px] text-[#241019]/55 mt-2">{i.value ? `Value ${money(i.value)} · ` : ''}{i.bid_count || 0} bid{i.bid_count === 1 ? '' : 's'}</p>
        <p data-testid={`auction-high-${i.id}`} className="font-serif text-[26px] text-[#B4247E] font-bold mt-1">{i.high_bid ? money(i.high_bid) : `Starts at ${money(i.start_bid)}`}</p>
        {i.mine && <p data-testid={`auction-mine-${i.id}`} className="text-[13px] font-semibold text-emerald-700 flex items-center gap-1"><Check size={14} /> You're winning</p>}
        {i.outbid && <p data-testid={`auction-outbid-${i.id}`} className="text-[13px] font-semibold text-amber-700">You've been outbid. Bid again!</p>}
        {token && onBid && !i.mine && (
          <div className="flex gap-2 mt-3">
            <input data-testid={`auction-amount-${i.id}`} type="number" min={i.next_min} placeholder={`${money(i.next_min)} or more`} value={amt} onChange={(e) => setAmt(e.target.value)} className={`${input} flex-1 min-w-0`} />
            <button data-testid={`auction-bid-${i.id}`} onClick={bid} className="btn-magenta rounded-xl px-5 font-semibold flex items-center gap-1.5"><Gavel size={15} /> Bid</button>
          </div>
        )}
        {msg && <p data-testid={`auction-msg-${i.id}`} className="text-[13px] text-[#3B0A2E] mt-2">{msg}</p>}
      </div>
    </div>
  );
};

export default function Auction() {
  const { eid } = useParams();
  const key = `csc_bidder_${eid}`;
  const [token, setToken] = useState(() => localStorage.getItem(key) || '');
  const [d, setD] = useState(null);
  const [f, setF] = useState({ name: '', email: '', phone: '' });
  const [err, setErr] = useState('');
  const load = useCallback(() => api.get(`/auction/${eid}`, { params: { token } }).then(({ data }) => setD(data)).catch(() => setD(false)), [eid, token]);
  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t); }, [load]);
  const register = async (e) => {
    e.preventDefault(); setErr('');
    try { const { data } = await api.post(`/auction/${eid}/register`, f); localStorage.setItem(key, data.token); setToken(data.token); } catch (ex) { setErr(ex?.response?.data?.detail || 'Please try again.'); }
  };
  if (d === null) return <div className="py-24 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!d) return <p className="py-24 text-center">Auction not found.</p>;
  const open = d.state === 'open';
  return (
    <div className="bg-[#F7EFE9] min-h-[80vh] px-5 py-10" data-testid="auction-page">
      <div className="max-w-5xl mx-auto">
        <p className="eyebrow text-[#B4247E]">Silent auction</p>
        <h1 className="font-serif text-[30px] sm:text-[38px] text-[#3B0A2E] font-semibold">{d.title}</h1>
        <p data-testid="auction-status" className="text-[14px] text-[#241019]/70 mt-1">{open ? `Bidding closes ${new Date(d.closes_at).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' })}` : d.state === 'closed' ? 'Bidding has closed. Winners have been emailed. Thank you!' : 'Bidding opens soon.'}</p>
        {open && !token && (
          <form onSubmit={register} data-testid="auction-register" className="bg-white rounded-3xl p-5 mt-5 grid sm:grid-cols-4 gap-2.5 border border-[#3B0A2E]/8">
            <input data-testid="auction-reg-name" required placeholder="Your name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={input} />
            <input data-testid="auction-reg-email" required type="email" placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={input} />
            <input data-testid="auction-reg-phone" required type="tel" placeholder="Phone" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value })} className={input} />
            <button data-testid="auction-reg-submit" className="btn-magenta rounded-xl py-3 font-semibold">Start bidding</button>
            {err && <p data-testid="auction-reg-error" className="sm:col-span-4 text-[13px] text-red-600">{err}</p>}
          </form>
        )}
        {d.me && <p data-testid="auction-me" className="text-[13.5px] text-[#3B0A2E] mt-3">Bidding as {d.me.name}</p>}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mt-6">
          {d.items.map((i) => <Item key={i.id} i={i} eid={eid} token={token} onBid={open ? load : null} />)}
        </div>
      </div>
    </div>
  );
}

export function AuctionPay() {
  const { token } = useParams();
  const [sp] = useSearchParams();
  const [w, setW] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { (sp.get('paid') ? api.post(`/auction/pay/${token}/confirm`) : api.get(`/auction/pay/${token}`)).then(({ data }) => setW(data)).catch(() => setW(false)); }, [token, sp]);
  const pay = async () => { setBusy(true); try { const { data } = await api.post(`/auction/pay/${token}`); window.location.href = data.url; } catch { setBusy(false); } };
  if (w === null) return <div className="py-24 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!w) return <p className="py-24 text-center">Not found.</p>;
  return (
    <div className="bg-[#F7EFE9] min-h-[70vh] py-16 px-5" data-testid="auction-pay">
      <div className="max-w-md mx-auto bg-white rounded-3xl p-8 text-center border border-[#3B0A2E]/8">
        <Trophy className="mx-auto text-[#CBA24B]" size={36} />
        <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mt-3">{w.title}</h1>
        <p className="text-[15px] text-[#241019]/70 mt-1">Winning bid {money(w.amount)}</p>
        {w.status === 'paid' ? <p data-testid="auction-paid" className="mt-5 font-semibold text-emerald-700">Paid. Thank you, {w.name.split(' ')[0]}!</p>
          : <button data-testid="auction-pay-btn" disabled={busy} onClick={pay} className="mt-6 btn-magenta rounded-full px-8 py-3.5 font-semibold disabled:opacity-60">{busy ? 'Opening…' : `Pay ${money(w.amount)}`}</button>}
      </div>
    </div>
  );
}
