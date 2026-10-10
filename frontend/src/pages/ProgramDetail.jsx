import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { eventImg } from './Events';
import { CtaLink } from './Initiatives';
import Reveal from '../components/Reveal';
import { TestimonialCard } from '../components/TestimonialCard';
import { ShareStory } from '../components/ShareStory';
import { ProgramSignup, SeatsBadge } from '../components/ProgramSignup';
import { imgSrc } from '../lib/useHomeContent';
import { Dialog, DialogContent, DialogTitle } from '../components/ui/dialog';
import { ArrowLeft, CheckCircle2, Loader2, Heart, ChevronLeft, ChevronRight } from 'lucide-react';

export default function ProgramDetail() {
  const { slug } = useParams();
  const [p, setP] = useState(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setP(null); setMissing(false);
    api.get(`/programs/${encodeURIComponent(slug)}`).then(({ data }) => setP(data)).catch(() => setMissing(true));
  }, [slug]);

  if (missing) {
    return (
      <section className="min-h-[60vh] flex flex-col items-center justify-center px-5 py-32 text-center" data-testid="program-not-found">
        <p className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-4">Program not found</p>
        <Link to="/initiatives" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">All Programs</Link>
      </section>
    );
  }
  if (!p) return <div className="flex justify-center py-48"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;

  return (
    <div data-testid="program-detail">
      <section className="relative pt-36 pb-20 lg:pt-44 lg:pb-28 overflow-hidden" style={{ background: '#29061F' }}>
        <img src={eventImg(p.image_url)} alt="" className="absolute inset-0 w-full h-full object-cover opacity-30" />
        <div className="absolute inset-0" style={{ background: 'linear-gradient(90deg, rgba(41,6,31,0.95) 30%, rgba(41,6,31,0.45))' }} />
        <div className="relative max-w-5xl mx-auto px-5 lg:px-8">
          <Link to="/initiatives" className="inline-flex items-center gap-2 text-[#F7EFE9]/70 hover:text-[#F7EFE9] text-[13.5px] mb-6"><ArrowLeft size={15} /> All Programs</Link>
          {p.category && <p className="eyebrow text-[#CBA24B] mb-3">{p.category}</p>}
          <h1 className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#F7EFE9] font-semibold max-w-3xl leading-tight" data-testid="program-title">{p.title}</h1>
          {p.summary && <p className="text-[#F7EFE9]/80 text-base md:text-lg mt-5 max-w-2xl leading-relaxed">{p.summary}</p>}
        </div>
      </section>

      {p.impact?.length > 0 && (
        <section className="csc-plum-bg py-12">
          <div className="max-w-5xl mx-auto px-5 lg:px-8 grid grid-cols-2 md:grid-cols-3 gap-8" data-testid="program-impact">
            {p.impact.map((s, i) => (
              <Reveal key={s.label} delay={i * 90} className="text-center">
                <p className="font-serif text-[#CBA24B] text-[40px] font-bold leading-none">{s.value}</p>
                <p className="text-[#F7EFE9]/75 text-[13.5px] mt-2">{s.label}</p>
              </Reveal>
            ))}
          </div>
        </section>
      )}

      <section className="py-16 lg:py-24">
        <div className="max-w-5xl mx-auto px-5 lg:px-8 grid lg:grid-cols-[1.6fr_1fr] gap-12">
          <Reveal>
            {p.body ? (
              <div className="text-[#241019]/80 text-[16px] leading-[1.85] whitespace-pre-line" data-testid="program-body">{p.body}</div>
            ) : (
              <p className="text-[#241019]/70 text-[16px] leading-relaxed">{p.summary}</p>
            )}
          </Reveal>
          <Reveal delay={120} className="space-y-6">
            {p.goals?.length > 0 && (
              <div className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8" data-testid="program-goals">
                <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-4">Program goals</h3>
                <ul className="space-y-3">
                  {p.goals.map((g) => (
                    <li key={g} className="flex gap-3 text-[14.5px] text-[#241019]/80"><CheckCircle2 size={18} className="text-[#B4247E] shrink-0 mt-0.5" /> {g}</li>
                  ))}
                </ul>
              </div>
            )}
            <div className="rounded-2xl p-7 text-white" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }}>
              <h3 className="font-serif text-[20px] font-semibold mb-2">Be part of it</h3>
              <p className="text-[#F7EFE9]/75 text-[14px] mb-4">Your time and generosity keep this program growing.</p>
              <SeatsBadge p={p} className="mb-4" />
              <div className="flex flex-wrap gap-3">
                <CtaLink to={p.cta_link} testid="program-cta" className="btn-gold rounded-full px-6 py-2.5 font-semibold text-[14px]">{p.cta_text}</CtaLink>
                <Link to="/donate" className="rounded-full px-5 py-2.5 font-semibold text-[14px] border border-white/25 hover:bg-white/10 flex items-center gap-1.5"><Heart size={15} /> Donate</Link>
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      <Gallery items={p.gallery || []} />

      <section className="py-16 lg:py-20" data-testid="program-testimonials">
        <div className="max-w-6xl mx-auto px-5 lg:px-8">
          {p.testimonials?.length > 0 && <>
            <h2 className="font-serif text-[30px] lg:text-[38px] text-[#3B0A2E] font-semibold mb-10 text-center">Voices from the program</h2>
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-7 mb-10">
              {p.testimonials.map((t, i) => <Reveal key={t.id || i} delay={(i % 3) * 100}><TestimonialCard t={t} /></Reveal>)}
            </div>
          </>}
          <div className="text-center">
            <p className="text-[#241019]/65 text-[15px] mb-4">Part of {p.title}? Share how it made a difference.</p>
            <ShareStory programSlug={p.slug} autoOpen={new URLSearchParams(window.location.search).get('share') === '1'} />
          </div>
        </div>
      </section>

      <div style={{ background: '#F7EFE9' }}><ProgramSignup program={p} /></div>
    </div>
  );
}

function Gallery({ items }) {
  const [idx, setIdx] = useState(null);
  if (!items.length) return null;
  const go = (d) => setIdx((i) => (i + d + items.length) % items.length);
  const cur = idx !== null ? items[idx] : null;
  return (
    <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }} data-testid="program-gallery">
      <div className="max-w-6xl mx-auto px-5 lg:px-8">
        <h2 className="font-serif text-[30px] lg:text-[38px] text-[#3B0A2E] font-semibold mb-8">In pictures</h2>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
          {items.map((g, i) => (
            <button key={g.url} onClick={() => setIdx(i)} className="img-zoom rounded-xl overflow-hidden aspect-[4/3] block" data-testid="program-gallery-photo">
              <img src={imgSrc(g.url)} alt={g.caption || ''} className="w-full h-full object-cover" />
            </button>
          ))}
        </div>
      </div>
      <Dialog open={idx !== null} onOpenChange={(o) => !o && setIdx(null)}>
        <DialogContent className="max-w-4xl p-3 bg-[#29061F] border-0" data-testid="program-gallery-lightbox">
          <DialogTitle className="sr-only">{cur?.caption || 'Program photo'}</DialogTitle>
          {cur && (
            <div className="relative">
              <img src={imgSrc(cur.url)} alt={cur.caption || ''} className="w-full max-h-[75vh] object-contain rounded-lg" />
              {cur.caption && <p className="text-[#F7EFE9]/85 text-[14px] text-center mt-3">{cur.caption}</p>}
              {items.length > 1 && <>
                <button onClick={() => go(-1)} className="absolute left-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/85 flex items-center justify-center" data-testid="gallery-prev-btn"><ChevronLeft size={20} /></button>
                <button onClick={() => go(1)} className="absolute right-2 top-1/2 -translate-y-1/2 w-10 h-10 rounded-full bg-white/85 flex items-center justify-center" data-testid="gallery-next-btn"><ChevronRight size={20} /></button>
              </>}
            </div>
          )}
        </DialogContent>
      </Dialog>
    </section>
  );
}
