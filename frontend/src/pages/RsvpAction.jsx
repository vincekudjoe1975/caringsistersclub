import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, CalendarX2, Ticket, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import { fmtDate, errMsg, CalendarButtons } from './Events';

function Shell({ children }) {
  return (
    <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
      <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="rsvp-action-page">{children}</div>
    </section>
  );
}

function EventSummary({ ev, guests }) {
  return (
    <div className="rounded-xl px-5 py-4 my-5 text-left text-[13.5px] text-[#3B0A2E]" style={{ background: '#faf2f7' }}>
      <p className="font-semibold text-[15px] mb-1">{ev.title}</p>
      <p>{fmtDate(ev.date)}{ev.time && <> &middot; {ev.time} ET</>}</p>
      {ev.location && <p>{ev.location}</p>}
      <p className="text-[#241019]/60 mt-1">Party of {guests}</p>
    </div>
  );
}

export default function RsvpAction() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);

  useEffect(() => {
    api.get(`/events/token/${encodeURIComponent(token)}`).then(({ data }) => setInfo(data)).catch((e) => setError(errMsg(e)));
  }, [token]);

  const act = async () => {
    setBusy(true);
    try { const { data } = await api.post(`/events/token/${encodeURIComponent(token)}`); setDone(data); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  };

  if (error) {
    return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Link unavailable</p>
      <p className="text-[14px] text-[#241019]/65 mb-6" data-testid="rsvp-action-error">{error}</p><Link to="/events" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">See Events</Link></Shell>;
  }
  if (!info) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;

  if (done) {
    return done.done === 'cancelled' ? (
      <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2" data-testid="rsvp-cancelled">Your RSVP is cancelled</p>
        <p className="text-[14px] text-[#241019]/65 mb-6">Thank you for letting us know. Your spot has been offered to a sister on the waitlist.</p><Link to="/events" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">Browse Events</Link></Shell>
    ) : (
      <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2" data-testid="spot-claimed">Your spot is confirmed!</p>
        <p className="text-[14px] text-[#241019]/65">A confirmation email is on its way. Add it to your calendar so you don't miss it.</p>
        <CalendarButtons gcal={done.gcal_url} ics={done.ics_url} /></Shell>
    );
  }

  if (info.kind === 'cancel') {
    return (
      <Shell>
        <CalendarX2 size={44} className="text-[#B4247E] mx-auto mb-3" />
        <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Cancel your RSVP?</p>
        <EventSummary ev={info.event} guests={info.guests} />
        <button onClick={act} disabled={busy} data-testid="confirm-cancel-rsvp-btn" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] disabled:opacity-60">
          {busy ? 'Cancelling…' : 'Yes, cancel my RSVP'}
        </button>
        <p className="mt-4"><Link to="/events" className="text-[13px] text-[#241019]/55 hover:text-[#3B0A2E]">Keep my spot</Link></p>
      </Shell>
    );
  }

  const expires = info.expires_at ? new Date(info.expires_at).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '';
  return (
    <Shell>
      <Ticket size={44} className="text-[#B4247E] mx-auto mb-3" />
      <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{info.state === 'open' ? `A spot is waiting for you, ${info.name}!` : info.state === 'claimed' ? 'Already claimed' : 'This invitation has expired'}</p>
      <EventSummary ev={info.event} guests={info.guests} />
      {info.state === 'open' ? (
        <>
          <button onClick={act} disabled={busy} data-testid="claim-spot-btn" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] disabled:opacity-60">{busy ? 'Claiming…' : 'Claim My Spot'}</button>
          {expires && <p className="text-[12.5px] text-[#241019]/55 mt-3" data-testid="claim-expires">Hold expires {expires}</p>}
        </>
      ) : (
        <p className="text-[14px] text-[#241019]/65" data-testid="claim-state">{info.state === 'claimed' ? "You've already claimed this spot. Check your email for the confirmation." : 'The spot was offered to the next person on the waitlist.'}</p>
      )}
    </Shell>
  );
}
