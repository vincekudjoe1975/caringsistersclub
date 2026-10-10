import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ListOrdered, CheckCircle2, AlertCircle, Ticket } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from './Events';

const Shell = ({ children }) => (
  <section className="min-h-[70vh] flex items-center justify-center px-5 py-32" style={{ background: '#F7EFE9' }}>
    <div className="bg-white rounded-[24px] max-w-lg w-full p-9 text-center border border-[#3B0A2E]/8" data-testid="waitlist-status-page">{children}</div>
  </section>
);

export default function WaitlistStatus() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [d, setD] = useState(null);
  const [error, setError] = useState('');
  useEffect(() => { api.get(`/waitlist/status?token=${encodeURIComponent(token)}`).then(({ data }) => setD(data)).catch((e) => setError(errMsg(e))); }, [token]);

  if (error) return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Link unavailable</p><p className="text-[14px] text-[#241019]/65" data-testid="waitlist-status-error">{error}</p></Shell>;
  if (!d) return <Shell><Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} /></Shell>;
  if (d.status === 'in') return <Shell><CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2" data-testid="waitlist-status-in">You're in!</p><p className="text-[14px] text-[#241019]/65 mb-6">You have a spot in <strong>{d.program}</strong>.</p>{d.slug && <Link to={`/initiatives/${d.slug}`} className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">View the Program</Link>}</Shell>;
  if (d.status === 'removed') return <Shell><AlertCircle size={44} className="text-[#B4247E] mx-auto mb-3" /><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2" data-testid="waitlist-status-removed">No longer on the waitlist</p><p className="text-[14px] text-[#241019]/65">Questions? Reply to any of our emails and our team will help.</p></Shell>;
  return (
    <Shell>
      <ListOrdered size={40} className="text-[#B4247E] mx-auto mb-3" />
      <p className="text-[14px] text-[#241019]/65">{d.name ? `Hi ${d.name}, your` : 'Your'} place on the <strong>{d.program}</strong> waitlist</p>
      <p className="font-serif text-[64px] text-[#B4247E] font-bold leading-none my-4" data-testid="waitlist-status-position">#{d.position}</p>
      <p className="text-[13.5px] text-[#241019]/60" data-testid="waitlist-status-total">of {d.total} sister{d.total === 1 ? '' : 's'} waiting</p>
      {d.status === 'offer' && (
        <div className="mt-6 rounded-xl p-5" style={{ background: '#fdf3e1' }}>
          <p className="font-semibold text-[#8a6a2c] mb-3 flex items-center justify-center gap-2"><Ticket size={16} /> A spot is being held for you!</p>
          <Link to={`/waitlist/claim?token=${d.claim_token}`} data-testid="waitlist-status-claim-link" className="btn-magenta rounded-full px-6 py-2.5 font-semibold text-[14px] inline-block">Claim My Spot</Link>
        </div>
      )}
    </Shell>
  );
}
