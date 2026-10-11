import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { Loader2, LogIn, CheckCircle2, Minus, Plus, CalendarDays, MapPin } from 'lucide-react';

const Frame = ({ children }) => (
  <div className="csc-hero-gradient min-h-screen flex items-center justify-center px-5 py-16">
    <div data-testid="self-checkin-page" className="bg-white rounded-3xl p-8 max-w-sm w-full text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>{children}</div>
  </div>
);

export default function SelfCheckIn() {
  const [sp] = useSearchParams();
  const mid = sp.get('m') || '', t = sp.get('t') || '';
  const { user } = useAuth();
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  const [guests, setGuests] = useState(0);
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    if (!user) return;
    api.get(`/members/self-checkin/${mid}`, { params: { t } }).then(({ data }) => { setD(data); setGuests(data.checked_in ? data.guests : data.rsvp_guests || 0); })
      .catch((e) => setErr(e?.response?.status === 403 ? 'Self check-in is for active members. Please see a staff member at the door.' : e?.response?.data?.detail || 'Could not load check-in.'));
  }, [user, mid, t]);
  const login = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(window.location.href)}`;
  };
  const checkIn = async () => {
    setBusy(true); setErr('');
    try { await api.post(`/members/self-checkin/${mid}`, { t, guests }); setD({ ...d, checked_in: true, guests }); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Check-in failed.'); }
    finally { setBusy(false); }
  };
  if (user === null) return <Frame><Loader2 className="animate-spin mx-auto text-[#B4247E]" /></Frame>;
  if (!user) return (
    <Frame>
      <p className="eyebrow text-[#CBA24B] mb-2">Caring Sisters Club</p>
      <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">Check yourself in</h1>
      <p className="text-[14px] text-[#241019]/65 mb-6">Sign in with the Google account you use for the member portal.</p>
      <button data-testid="self-checkin-login" onClick={login} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2"><LogIn size={18} /> Continue with Google</button>
    </Frame>
  );
  if (err && !d) return <Frame><p data-testid="self-checkin-error" className="text-[14.5px] text-[#241019]/75">{err}</p></Frame>;
  if (!d) return <Frame><Loader2 className="animate-spin mx-auto text-[#B4247E]" /></Frame>;
  return (
    <Frame>
      <p className="eyebrow text-[#CBA24B] mb-2">Welcome, {(user.name || 'Sister').split(' ')[0]}</p>
      <h1 data-testid="self-checkin-title" className="font-serif text-[25px] text-[#3B0A2E] font-semibold leading-tight">{d.title}</h1>
      <div className="flex flex-wrap justify-center gap-3 text-[12.5px] text-[#241019]/60 mt-2 mb-6">
        <span className="flex items-center gap-1"><CalendarDays size={13} /> {new Date(d.date + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' })}</span>
        {d.location && <span className="flex items-center gap-1"><MapPin size={13} /> {d.location}</span>}
      </div>
      {d.checked_in ? (
        <div data-testid="self-checkin-done"><CheckCircle2 size={56} className="mx-auto text-green-600 mb-3" /><p className="font-semibold text-[#3B0A2E] text-[17px]">You're checked in!</p>
          <p className="text-[13.5px] text-[#241019]/60 mt-1">{d.guests ? `Plus ${d.guests} guest${d.guests === 1 ? '' : 's'}. ` : ''}Enjoy the gathering.</p></div>
      ) : !d.open ? (
        <p data-testid="self-checkin-closed" className="text-[14px] text-[#241019]/70">Self check-in opens on the day of the gathering and closes when staff finish attendance.</p>
      ) : (
        <>
          <p className="text-[13.5px] font-semibold text-[#3B0A2E] mb-2">Guests with you</p>
          <div className="flex items-center justify-center gap-4 mb-6">
            <button data-testid="self-guest-minus" onClick={() => setGuests(Math.max(0, guests - 1))} className="w-11 h-11 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center"><Minus size={18} /></button>
            <span data-testid="self-guest-count" className="text-[28px] font-semibold text-[#3B0A2E] w-10">{guests}</span>
            <button data-testid="self-guest-plus" onClick={() => setGuests(Math.min(20, guests + 1))} className="w-11 h-11 rounded-full border border-[#3B0A2E]/15 flex items-center justify-center"><Plus size={18} /></button>
          </div>
          <button data-testid="self-checkin-btn" onClick={checkIn} disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">{busy ? <Loader2 size={18} className="animate-spin" /> : <CheckCircle2 size={18} />} Check me in</button>
        </>
      )}
      {err && <p data-testid="self-checkin-msg" className="text-red-600 text-[13px] mt-3">{err}</p>}
    </Frame>
  );
}
