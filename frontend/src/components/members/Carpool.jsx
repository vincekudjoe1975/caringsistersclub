import React, { useCallback, useEffect, useState } from 'react';
import { Car, Hand, Phone, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

const chip = (on) => `min-h-[40px] rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5 transition-colors ${on ? 'bg-[#CBA24B] text-[#3B0A2E]' : 'bg-white/10 text-[#F7EFE9] border border-white/20 hover:bg-white/20'}`;

const Person = ({ p, testid }) => (
  <li data-testid={testid} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[13.5px]">
    <span className="font-semibold text-[#F7EFE9]">{p.name}</span>{p.city && <span className="text-[#F7EFE9]/60">{p.city}</span>}
    {p.phone ? <a href={`tel:${p.phone}`} className="text-[#CBA24B] font-semibold flex items-center gap-1"><Phone size={12} /> {p.phone}</a> : <span className="text-[#F7EFE9]/50">No phone on profile</span>}
  </li>
);

export const Carpool = ({ g }) => {
  const [c, setC] = useState(null);
  const [seats, setSeats] = useState(3);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const load = useCallback(() => api.get(`/members/gatherings/${g.id}/carpool`).then(({ data }) => { setC(data); if (data.me?.seats) setSeats(data.me.seats); }).catch(() => {}), [g.id]);
  useEffect(() => { load(); }, [load]);
  const run = async (fn) => { setBusy(true); setErr(''); try { const { data } = await fn(); setC(data); } catch (ex) { setErr(ex?.response?.data?.detail || 'Something went wrong.'); } finally { setBusy(false); } };
  const setRole = (role) => run(() => api.put(`/members/gatherings/${g.id}/carpool`, { role, seats: Number(seats) || 0 }));
  if (!c) return null;
  const me = c.me;
  return (
    <div data-testid={`carpool-${g.id}`} className="mt-4 pt-4 border-t border-white/15">
      <p className="text-[13px] font-semibold text-[#F7EFE9] mb-2 flex items-center gap-1.5"><Car size={14} /> Carpool <span className="font-normal text-[#F7EFE9]/60">· {c.drivers} driving, {c.needs} need a ride</span></p>
      <div className="flex flex-wrap items-center gap-2">
        <button data-testid={`carpool-need-${g.id}`} disabled={busy} onClick={() => setRole(me?.role === 'need' ? 'none' : 'need')} className={chip(me?.role === 'need')}><Hand size={13} /> I need a ride</button>
        <button data-testid={`carpool-drive-${g.id}`} disabled={busy} onClick={() => setRole(me?.role === 'drive' ? 'none' : 'drive')} className={chip(me?.role === 'drive')}><Car size={13} /> I can drive</button>
        <label className="text-[12.5px] text-[#F7EFE9]/80 flex items-center gap-2">Seats
          <input data-testid={`carpool-seats-${g.id}`} type="number" min="1" max="8" value={seats} onChange={(e) => setSeats(e.target.value)} className="w-16 rounded-full px-3 py-1.5 text-[13px] text-[#241019]" />
        </label>
        {me?.role === 'drive' && Number(seats) !== me.seats && <button data-testid={`carpool-seats-save-${g.id}`} disabled={busy} onClick={() => setRole('drive')} className="text-[12.5px] font-semibold text-[#CBA24B] underline">Update seats</button>}
        {busy && <Loader2 size={14} className="animate-spin text-[#F7EFE9]" />}
      </div>
      {me?.role === 'need' && (me.driver
        ? <div className="mt-3"><p className="text-[12.5px] text-[#F7EFE9]/70 mb-1">Your driver</p><ul><Person p={me.driver} testid={`carpool-driver-${g.id}`} /></ul></div>
        : <p data-testid={`carpool-waiting-${g.id}`} className="text-[12.5px] text-[#F7EFE9]/70 mt-2">You're on the ride list. We'll alert you when a sister offers you a seat{me.city ? '' : '. Add your city in My Profile so nearby drivers find you'}.</p>)}
      {me?.role === 'drive' && (
        <div className="mt-3 space-y-3">
          <p data-testid={`carpool-seats-left-${g.id}`} className="text-[12.5px] text-[#F7EFE9]/70">{me.seats_left} of {me.seats} seat{me.seats === 1 ? '' : 's'} open</p>
          {me.riders.length > 0 && <div><p className="text-[12.5px] text-[#F7EFE9]/70 mb-1">Your riders</p><ul className="space-y-1">{me.riders.map((r) => <Person key={r.user_id} p={r} testid={`carpool-rider-${r.user_id}`} />)}</ul></div>}
          {c.riders_waiting.length > 0 && (
            <div><p className="text-[12.5px] text-[#F7EFE9]/70 mb-1">Sisters who need a ride</p>
              <ul className="space-y-1.5">{c.riders_waiting.map((r) => (
                <li key={r.user_id} className="flex items-center gap-3 text-[13.5px]">
                  <span className="text-[#F7EFE9] font-semibold">{r.name}</span><span className="text-[#F7EFE9]/60">{r.city || 'City not set'}</span>
                  <button data-testid={`carpool-offer-${r.user_id}`} disabled={busy || me.seats_left <= 0} onClick={() => run(() => api.post(`/members/gatherings/${g.id}/carpool/offer/${r.user_id}`))} className="ml-auto rounded-full px-3 py-1.5 text-[12.5px] font-semibold bg-[#CBA24B] text-[#3B0A2E] disabled:opacity-50">Offer ride</button>
                </li>
              ))}</ul>
            </div>
          )}
        </div>
      )}
      {err && <p data-testid={`carpool-error-${g.id}`} className="text-[12.5px] text-red-200 mt-2">{err}</p>}
    </div>
  );
};
