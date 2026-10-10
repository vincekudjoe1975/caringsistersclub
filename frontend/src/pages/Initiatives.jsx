import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../lib/api';
import { eventImg } from './Events';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { SeatsBadge } from '../components/ProgramSignup';
import { ArrowRight, Loader2, Layers } from 'lucide-react';

export const CtaLink = ({ to, className, children, testid }) => (to.startsWith('https://')
  ? <a href={to} target="_blank" rel="noopener noreferrer" className={className} data-testid={testid}>{children}</a>
  : <Link to={to} className={className} data-testid={testid}>{children}</Link>);

function ProgramCard({ item }) {
  return (
    <div className="card-hover bg-white rounded-2xl overflow-hidden h-full border border-[#3B0A2E]/8 flex flex-col" data-testid="program-card">
      <Link to={`/initiatives/${item.slug}`} className="img-zoom h-52 block">
        <img src={eventImg(item.image_url)} alt={item.title} className="w-full h-full object-cover" />
      </Link>
      <div className="p-7 flex flex-col flex-1">
        {item.category && <span className="eyebrow text-[#CBA24B]">{item.category}</span>}
        <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mt-2 mb-3">
          <Link to={`/initiatives/${item.slug}`} className="hover:text-[#B4247E] transition-colors">{item.title}</Link>
        </h3>
        <p className="text-[#241019]/70 text-[14.5px] leading-relaxed mb-5 flex-1">{item.summary}</p>
        <SeatsBadge p={item} className="mb-4 self-start" />
        <div className="flex items-center gap-5">
          <Link to={`/initiatives/${item.slug}`} data-testid="program-learn-more" className="inline-flex items-center gap-2 text-[#B4247E] font-semibold text-[14px] link-underline">
            Learn More <ArrowRight size={16} />
          </Link>
          <CtaLink to={item.cta_link} className="text-[13.5px] font-semibold text-[#3B0A2E]/70 hover:text-[#3B0A2E]">{item.cta_text}</CtaLink>
        </div>
      </div>
    </div>
  );
}

export default function Initiatives() {
  const [data, setData] = useState(null);
  const [active, setActive] = useState('All');

  useEffect(() => {
    api.get('/programs').then(({ data: d }) => setData(d)).catch((e) => { console.error('Programs: load failed', e); setData({ items: [], categories: [] }); });
  }, []);

  const items = data?.items || [];
  const used = new Set(items.map((i) => i.category));
  const categories = ['All', ...(data?.categories || []).filter((c) => used.has(c))];
  const filtered = active === 'All' ? items : items.filter((i) => i.category === active);

  return (
    <div>
      <PageHero
        kicker="Programs & Initiatives"
        title="Programs that turn vision into impact"
        subtitle="From business acceleration to housing support and community care, explore the initiatives powering our sisterhood."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          {data === null ? (
            <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
          ) : items.length === 0 ? (
            <div className="bg-white rounded-2xl p-14 text-center border border-[#3B0A2E]/8" data-testid="programs-empty">
              <Layers size={40} className="text-[#B4247E] mx-auto mb-3" />
              <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">New programs are on the way</p>
            </div>
          ) : (
            <>
              {categories.length > 2 && (
                <div className="flex flex-wrap gap-3 mb-12">
                  {categories.map((c) => (
                    <button key={c} onClick={() => setActive(c)} data-testid={`program-filter-${c.toLowerCase().replace(/\s+/g, '-')}`}
                      className={`px-5 py-2 rounded-full text-[14px] font-semibold transition-all ${active === c ? 'text-white' : 'text-[#3B0A2E] hover:bg-[#f2e6ee]'}`}
                      style={active === c ? { background: '#B4247E' } : { background: '#F7EFE9' }}>
                      {c}
                    </button>
                  ))}
                </div>
              )}
              <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-7">
                {filtered.map((item, i) => (
                  <Reveal key={item.id} delay={(i % 3) * 100}><ProgramCard item={item} /></Reveal>
                ))}
              </div>
            </>
          )}
        </div>
      </section>

      <section className="csc-plum-bg py-14">
        <div className="max-w-5xl mx-auto px-5 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <h3 className="font-serif text-[#F7EFE9] text-[26px] md:text-[30px] font-semibold">Want to bring a program to your city?</h3>
          <Link to="/contact" className="btn-gold rounded-full px-8 py-3.5 font-semibold whitespace-nowrap">Start a Chapter</Link>
        </div>
      </section>
    </div>
  );
}
