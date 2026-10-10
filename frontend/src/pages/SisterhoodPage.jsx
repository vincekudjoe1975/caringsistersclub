import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Loader2, Award } from 'lucide-react';
import { api, BACKEND_URL } from '../lib/api';
import { ShareBar } from './YearInReview';

export default function SisterhoodPage() {
  const { token } = useParams();
  const [d, setD] = useState(undefined);
  useEffect(() => { api.get(`/sisterhood/${encodeURIComponent(token)}`).then(({ data }) => setD(data)).catch(() => setD(null)); }, [token]);
  if (d === undefined) return <div className="pt-40 pb-20 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  if (d === null) return <section className="pt-40 pb-24 text-center px-5" data-testid="sisterhood-not-found"><p className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-4">Page not found</p><Link to="/" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px]">Go Home</Link></section>;
  return (
    <section className="pt-36 pb-20 px-5" style={{ background: '#F7EFE9' }} data-testid="sisterhood-page">
      <div className="max-w-4xl mx-auto text-center">
        <p className="text-[12px] uppercase tracking-[0.2em] font-semibold text-[#B4247E] mb-2 flex items-center justify-center gap-1.5"><Award size={14} /> Sisterhood badges</p>
        <h1 className="font-serif text-4xl sm:text-5xl text-[#3B0A2E] font-semibold mb-3" data-testid="sisterhood-name">{d.name || 'A proud sister'}</h1>
        <p className="text-[16px] text-[#241019]/65 mb-10" data-testid="sisterhood-count">{d.badges.length} badge{d.badges.length === 1 ? '' : 's'} earned with The Caring Sisters Club</p>
        {d.badges.length === 0 ? <p className="text-[14px] text-[#241019]/55 mb-10">No badges yet. The first one is just around the corner!</p> : (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-5 mb-12">
            {d.badges.map((b, i) => {
              const inner = (
                <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 card-hover h-full" style={{ animation: `fadeUp .5s ease ${i * 70}ms both` }}>
                  <div className="mx-auto mb-4 w-20 h-20 rounded-full flex items-center justify-center border-[4px] border-[#CBA24B]" style={{ background: '#3B0A2E' }}><span className="font-serif text-[24px] font-bold text-[#CBA24B]">{b.seal}</span></div>
                  <p className="font-semibold text-[#3B0A2E] text-[14.5px]" data-testid="sisterhood-badge-label">{b.label}</p>
                  <p className="text-[11.5px] text-[#241019]/50 mt-1">{b.kind === 'participant' ? 'Sisterhood' : 'Volunteer'} · {new Date(b.awarded_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}</p>
                </div>
              );
              return b.share_token ? <Link key={i} to={`/badge/${b.share_token}`} data-testid="sisterhood-badge">{inner}</Link> : <div key={i} data-testid="sisterhood-badge">{inner}</div>;
            })}
          </div>
        )}
        <img src={`${BACKEND_URL}/api/share/sisterhood/${token}/card.png`} alt="All my badges" className="w-full max-w-xl mx-auto rounded-2xl shadow-lg mb-8" data-testid="sisterhood-card-image" />
        <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-4">Share all my badges</h2>
        <ShareBar testid="sisterhood" url={`${BACKEND_URL}/api/share/sisterhood/${token}`} text={`I've earned ${d.badges.length} badges with The Caring Sisters Club!`} />
      </div>
    </section>
  );
}
