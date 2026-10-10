import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, Award } from 'lucide-react';
import { api, BACKEND_URL } from '../lib/api';
import { ShareBar } from './YearInReview';

export default function BadgePage() {
  const { token } = useParams();
  const [b, setB] = useState(undefined);
  useEffect(() => { api.get(`/badges/${encodeURIComponent(token)}`).then(({ data }) => setB(data)).catch(() => setB(null)); }, [token]);

  if (b === undefined) return <div className="pt-40 pb-20 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  if (b === null) return (
    <section className="pt-40 pb-24 text-center px-5" data-testid="badge-not-found">
      <p className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-4">Badge not found</p>
      <Link to="/volunteer" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px]">Volunteer With Us</Link>
    </section>
  );
  const date = new Date(b.awarded_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
  return (
    <section className="pt-36 pb-20 px-5" style={{ background: '#F7EFE9' }} data-testid="badge-page">
      <div className="max-w-3xl mx-auto text-center">
        <div className="mx-auto mb-7 w-44 h-44 rounded-full flex items-center justify-center border-[6px] border-[#CBA24B] shadow-xl" style={{ background: '#3B0A2E' }}>
          <span className="font-serif text-[56px] font-bold text-[#CBA24B]" data-testid="badge-threshold">{b.threshold}h</span>
        </div>
        <p className="text-[12px] uppercase tracking-[0.2em] font-semibold text-[#B4247E] mb-2 flex items-center justify-center gap-1.5"><Award size={14} /> Volunteer badge</p>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#3B0A2E] font-semibold mb-3" data-testid="badge-name">{b.name}</h1>
        <p className="text-[17px] text-[#241019]/70 mb-1">earned the <strong className="text-[#B4247E]" data-testid="badge-label">{b.label}</strong> badge</p>
        <p className="text-[13px] text-[#241019]/50 mb-10">Awarded {date} by The Caring Sisters Club</p>
        <img src={`${BACKEND_URL}/api/share/badge/${token}/card.png`} alt={`${b.label} badge card`} className="w-full max-w-xl mx-auto rounded-2xl shadow-lg mb-10" data-testid="badge-card-image" />
        <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-4">Share my badge</h2>
        <ShareBar testid="badge" url={`${BACKEND_URL}/api/share/badge/${token}`} text={`I earned the ${b.label} volunteer badge with The Caring Sisters Club!`} />
        <Link to="/volunteer" data-testid="badge-volunteer-link" className="inline-block mt-10 btn-gold rounded-full px-7 py-3 font-semibold text-[14px]">Volunteer with us too</Link>
      </div>
    </section>
  );
}
