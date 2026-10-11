import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { gallery as mockGallery } from '../mock/mock';
import { api, mediaSrc } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { X, ChevronLeft, ChevronRight, CalendarHeart, Layers } from 'lucide-react';

const CHIPS = [['all', 'All'], ['event', 'Events'], ['program', 'Programs']];

function Lightbox({ items, idx, setIdx }) {
  const g = items[idx];
  const go = useCallback((d) => setIdx((p) => (p + d + items.length) % items.length), [items.length, setIdx]);
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') setIdx(null); else if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1); };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [go, setIdx]);
  return (
    <div data-testid="gallery-lightbox" className="fixed inset-0 z-[60] flex items-center justify-center p-4 md:p-8 animate-[fadeIn_.25s_ease]" style={{ background: 'rgba(41,6,31,0.94)' }} onClick={() => setIdx(null)}>
      <button data-testid="gallery-lightbox-close" className="absolute top-5 right-5 text-[#F7EFE9] hover:text-[#CBA24B] z-10" onClick={() => setIdx(null)}><X size={32} /></button>
      <button data-testid="gallery-lightbox-prev" className="absolute left-2 md:left-6 text-[#F7EFE9] hover:text-[#CBA24B] z-10" onClick={(e) => { e.stopPropagation(); go(-1); }}><ChevronLeft size={40} /></button>
      <div key={idx} className="max-w-6xl w-full flex flex-col lg:flex-row gap-6 items-center animate-[zoomIn_.35s_ease]" onClick={(e) => e.stopPropagation()}>
        <img src={g.src} alt={g.caption} className="w-full lg:w-[68%] max-h-[62vh] lg:max-h-[80vh] object-contain rounded-xl" />
        {(g.caption || g.description || g.tag_label) && (
          <div className="lg:flex-1 w-full text-[#F7EFE9] max-h-[30vh] lg:max-h-[80vh] overflow-y-auto">
            {g.tag_label && <p className="eyebrow text-[#CBA24B] mb-2 flex items-center gap-1.5">{g.tag_type === 'event' ? <CalendarHeart size={13} /> : <Layers size={13} />} {g.tag_label}</p>}
            {g.caption && <h3 data-testid="gallery-lightbox-title" className="font-serif text-[24px] lg:text-[28px] leading-tight mb-3">{g.caption}</h3>}
            {g.description && <p data-testid="gallery-lightbox-desc" className="text-[14.5px] leading-relaxed text-[#F7EFE9]/80 whitespace-pre-line">{g.description}</p>}
            {g.tag_type === 'program' && g.tag_ref && <Link to={`/initiatives/${g.tag_ref}`} className="inline-block mt-5 text-[13px] font-semibold text-[#CBA24B] hover:underline">Explore this program →</Link>}
            {g.tag_type === 'event' && <Link to="/events" className="inline-block mt-5 text-[13px] font-semibold text-[#CBA24B] hover:underline">See upcoming events →</Link>}
          </div>
        )}
      </div>
      <button data-testid="gallery-lightbox-next" className="absolute right-2 md:right-6 text-[#F7EFE9] hover:text-[#CBA24B] z-10" onClick={(e) => { e.stopPropagation(); go(1); }}><ChevronRight size={40} /></button>
    </div>
  );
}

export default function Gallery() {
  const [idx, setIdx] = useState(null);
  const [all, setAll] = useState(mockGallery);
  const [chip, setChip] = useState('all');
  const [label, setLabel] = useState('');

  useEffect(() => {
    api.get('/media?category=gallery').then(({ data }) => {
      if (data && data.length) setAll(data.map((d) => ({ src: mediaSrc(d.url), caption: d.title || '', description: d.description || '', tag_type: d.tag_type || '', tag_label: d.tag_label || '', tag_ref: d.tag_ref || '', uploaded: true })));
    }).catch((e) => console.error('Gallery: failed to load uploaded media, using defaults', e));
  }, []);

  const labels = useMemo(() => [...new Set(all.filter((g) => chip !== 'all' && g.tag_type === chip && g.tag_label).map((g) => g.tag_label))], [all, chip]);
  const items = all.filter((g) => (chip === 'all' || g.tag_type === chip) && (!label || g.tag_label === label));
  const hasTags = all.some((g) => g.tag_type);

  return (
    <div>
      <PageHero kicker="Impact Media Gallery" title="Moments from our sisterhood" subtitle="A look at the summits, service drives, and celebrations that show our impact in action." />
      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          {hasTags && (
            <div className="mb-10">
              <div className="flex flex-wrap gap-2">
                {CHIPS.map(([k, l]) => (
                  <button key={k} data-testid={`gallery-chip-${k}`} onClick={() => { setChip(k); setLabel(''); }} className={`px-5 py-2 rounded-full text-[13.5px] font-semibold transition-colors ${chip === k ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12 hover:border-[#B4247E]'}`}>{l}</button>
                ))}
              </div>
              {labels.length > 1 && (
                <div className="flex flex-wrap gap-2 mt-3 animate-[fadeIn_.3s_ease]">
                  {labels.map((l) => <button key={l} data-testid={`gallery-label-${l}`} onClick={() => setLabel(label === l ? '' : l)} className={`px-3.5 py-1.5 rounded-full text-[12.5px] font-semibold transition-colors ${label === l ? 'bg-[#B4247E] text-white' : 'bg-[#faf2f7] text-[#B4247E]'}`}>{l}</button>)}
                </div>
              )}
            </div>
          )}
          {!items.length && <p data-testid="gallery-empty" className="text-[#241019]/55 py-10">No photos in this category yet.</p>}
          <div className="columns-1 sm:columns-2 lg:columns-3 gap-5 [&>*]:mb-5" data-testid="gallery-grid">
            {items.map((g, i) => (
              <Reveal key={`${g.src}-${i}`} delay={(i % 3) * 80}>
                <button data-testid={`gallery-item-${i}`} onClick={() => setIdx(i)} className="block w-full img-zoom rounded-2xl overflow-hidden relative group">
                  <img src={g.src} alt={g.caption} className={`w-full object-cover ${g.uploaded ? '' : g.tall ? 'h-[420px]' : 'h-[290px]'}`} />
                  {g.tag_label && <span className="absolute top-3 left-3 bg-white/90 text-[#3B0A2E] text-[11px] font-semibold rounded-full px-3 py-1">{g.tag_label}</span>}
                  <div className="absolute inset-0 flex flex-col justify-end p-5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 text-left" style={{ background: 'linear-gradient(transparent 45%, rgba(41,6,31,0.85))' }}>
                    <p className="text-[#F7EFE9] text-[15px] font-semibold">{g.caption}</p>
                    {g.description && <p className="text-[#F7EFE9]/75 text-[12.5px] line-clamp-2 mt-1">{g.description}</p>}
                  </div>
                </button>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
      {idx !== null && items[idx] && <Lightbox items={items} idx={idx} setIdx={setIdx} />}
    </div>
  );
}
