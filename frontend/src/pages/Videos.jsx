import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { Play, X, Youtube, Loader2, ExternalLink } from 'lucide-react';

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' }) : '');

function Player({ v, onClose }) {
  useEffect(() => {
    const k = (e) => e.key === 'Escape' && onClose();
    const o = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', k);
    return () => { window.removeEventListener('keydown', k); document.body.style.overflow = o; };
  }, [onClose]);
  return (
    <div data-testid="video-player-modal" role="dialog" aria-modal="true" aria-label={v.title} onClick={onClose} className="fixed inset-0 z-[70] flex items-center justify-center p-4 md:p-10 animate-[fadeIn_.25s_ease]" style={{ background: 'rgba(41,6,31,0.94)' }}>
      <button data-testid="video-player-close" onClick={onClose} aria-label="Close video" className="absolute top-3 right-3 md:top-5 md:right-5 p-2 text-[#F7EFE9] hover:text-[#CBA24B]"><X size={32} /></button>
      <div onClick={(e) => e.stopPropagation()} className={`w-full animate-[zoomIn_.35s_ease] ${v.short ? 'max-w-[min(420px,calc(72vh*9/16))]' : 'max-w-5xl'}`}>
        <div className="relative w-full rounded-2xl overflow-hidden bg-black" style={{ aspectRatio: v.short ? '9 / 16' : '16 / 9' }}>
          <iframe data-testid="video-player-iframe" title={v.title} src={`https://www.youtube.com/embed/${v.id}?autoplay=1&rel=0&playsinline=1&modestbranding=1`} allow="autoplay; encrypted-media; picture-in-picture; fullscreen" referrerPolicy="strict-origin-when-cross-origin" allowFullScreen className="absolute inset-0 w-full h-full" />
        </div>
        <div className="flex flex-wrap items-start justify-between gap-3 mt-4 text-[#F7EFE9]">
          <div><h3 className="font-serif text-[20px] md:text-[24px] leading-tight">{v.title}</h3>{fmt(v.published) !== v.title && <p className="text-[13px] text-[#F7EFE9]/60 mt-1">{fmt(v.published)}</p>}</div>
          <a href={`https://www.youtube.com/watch?v=${v.id}`} target="_blank" rel="noreferrer" data-testid="video-player-youtube-link" className="text-[13px] font-semibold text-[#CBA24B] flex items-center gap-1.5 hover:underline">Watch on YouTube <ExternalLink size={13} /></a>
        </div>
        {v.description && <p className="text-[14px] text-[#F7EFE9]/75 mt-3 whitespace-pre-line max-h-[18vh] overflow-y-auto">{v.description}</p>}
      </div>
    </div>
  );
}

const Card = ({ v, i, onPlay }) => (
  <Reveal delay={(i % 4) * 70}>
    <button data-testid={`video-card-${v.id}`} onClick={() => onPlay(v)} className="group text-left w-full">
      <span className="relative block rounded-2xl overflow-hidden bg-[#3B0A2E]" style={{ aspectRatio: v.short ? '9 / 16' : '16 / 9' }}>
        <img src={v.thumbnail} alt={v.title} loading="lazy" className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" />
        <span className="absolute inset-0 bg-gradient-to-t from-[#29061F]/70 via-transparent to-transparent" />
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="w-16 h-16 rounded-full bg-[#F7EFE9]/90 text-[#B4247E] flex items-center justify-center shadow-xl transition-transform duration-300 group-hover:scale-110"><Play size={26} className="ml-1" fill="currentColor" /></span>
        </span>
      </span>
      <span className="block mt-3 font-serif text-[17px] text-[#3B0A2E] font-semibold leading-snug group-hover:text-[#B4247E] transition-colors">{v.title}</span>
      {fmt(v.published) !== v.title && <span className="block text-[12.5px] text-[#241019]/55 mt-0.5">{fmt(v.published)}</span>}
    </button>
  </Reveal>
);

const Section = ({ title, items, short, onPlay, testid }) => (
  <div className="mb-16 last:mb-0" data-testid={testid}>
    {title && <h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-6">{title}</h2>}
    <div className={short ? 'grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-x-5 gap-y-9' : 'grid sm:grid-cols-2 lg:grid-cols-3 gap-x-7 gap-y-10'}>
      {items.map((v, i) => <Card key={v.id} v={v} i={i} onPlay={onPlay} />)}
    </div>
  </div>
);

export default function Videos() {
  const [d, setD] = useState(null);
  const [playing, setPlaying] = useState(null);
  useEffect(() => { api.get('/videos').then(({ data }) => setD(data)).catch(() => setD({ items: [], channel_url: '' })); }, []);
  const channel = d?.channel_url || 'https://www.youtube.com/@CaringSisters-m7b';
  return (
    <div data-testid="videos-page">
      <PageHero kicker="Videos" title="Watch the sisterhood in action" subtitle="Highlights, gatherings, and stories from Caring Sisters Club, straight from our YouTube channel." />
      <section className="bg-[#F7EFE9] py-16 md:py-20">
        <div className="max-w-7xl mx-auto px-5 lg:px-10">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-10">
            <p className="text-[14px] text-[#241019]/65 max-w-xl">New uploads appear here automatically.</p>
            <a href={`${channel}?sub_confirmation=1`} target="_blank" rel="noreferrer" data-testid="videos-subscribe-btn" className="btn-magenta rounded-full px-6 py-3 font-semibold flex items-center gap-2"><Youtube size={18} /> Subscribe on YouTube</a>
          </div>
          {!d ? <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={28} /></div>
            : d.items.length === 0 ? (
              <div data-testid="videos-empty" className="text-center py-16"><p className="text-[#241019]/60 mb-4">Videos are on their way. In the meantime, visit our channel.</p><a href={channel} target="_blank" rel="noreferrer" className="font-semibold text-[#B4247E] hover:underline">Open our YouTube channel</a></div>
            ) : (
              <div data-testid="videos-grid">
                {(() => { const long = d.items.filter((v) => !v.short); const shorts = d.items.filter((v) => v.short); return <>
                  {long.length > 0 && <Section title={shorts.length ? 'Videos' : ''} items={long} onPlay={setPlaying} testid="videos-long" />}
                  {shorts.length > 0 && <Section title={long.length ? 'Shorts' : ''} items={shorts} short onPlay={setPlaying} testid="videos-shorts" />}
                </>; })()}
              </div>
            )}
        </div>
      </section>
      {playing && <Player v={playing} onClose={() => setPlaying(null)} />}
    </div>
  );
}
