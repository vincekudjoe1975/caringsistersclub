import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, Ticket, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from './Events';

const Shell = ({ children }) => (
  <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
    <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="waitlist-claim-page">{children}</div>
  </section>
);

const MESSAGES = {
  expired: ['This offer has expired', "You're still on the waitlist, and we'll let you know if another spot opens."],
  full: ['This spot was just taken', "Someone claimed it moments before you. You're still on the waitlist."],
};

export default function WaitlistClaim() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [info, setInfo] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get(`/waitlist/offer?token=${encodeURIComponent(token)}`).then(({ data }) => setInfo(data)).catch((e) => setError(errMsg(e))); }, [token]);

  const claim = async () => {
    setBusy(true);
    try { const { data } = await api.post('/waitlist/claim', { token }); setInfo({ ...info, status: data.status }); }
    catch (e) { setError(errMsg(e)); }
    finally { setBusy(false); }
  };

  if (error) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Spot unavailable</p><p className="text-[14px] text-[#241019]/65 mb-6" data-testid="waitlist-claim-error">{error}</p><Link to="/initiatives" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">See Programs</Link></Shell>;
  if (!info) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;
  if (info.status === 'claimed') return <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2" data-testid="waitlist-claimed">You're in!</p><p className="text-[14px] text-[#241019]/65 mb-6">Your spot in <strong>{info.program}</strong> is confirmed. Our team will reach out with next steps.</p><Link to={`/initiatives/${info.slug}`} className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">View the Program</Link></Shell>;
  if (MESSAGES[info.status]) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2" data-testid="waitlist-claim-state">{MESSAGES[info.status][0]}</p><p className="text-[14px] text-[#241019]/65">{MESSAGES[info.status][1]}</p></Shell>;
  const expires = info.expires ? new Date(info.expires).toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' }) : '';
  return (
    <Shell>
      <Ticket size={44} className="text-[#B4247E] mx-auto mb-3" />
      <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">A spot is waiting for you{info.name ? `, ${info.name}` : ''}!</p>
      <p className="text-[14px] text-[#241019]/65 my-4">A seat opened in <strong>{info.program}</strong>.</p>
      <button onClick={claim} disabled={busy} data-testid="waitlist-claim-btn" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] disabled:opacity-60">{busy ? 'Claiming…' : 'Claim My Spot'}</button>
      {expires && <p className="text-[12.5px] text-[#241019]/55 mt-3" data-testid="waitlist-claim-expires">Offer expires {expires}</p>}
    </Shell>
  );
}
