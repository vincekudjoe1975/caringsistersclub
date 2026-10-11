import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api, mediaSrc } from '../lib/api';
import Reveal from '../components/Reveal';
import { Lightbox } from './Gallery';
import { Loader2, ArrowLeft, Play } from 'lucide-react';

export default function GalleryAlbum() {
  const { slug } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState(false);
  const [idx, setIdx] = useState(null);
  useEffect(() => { api.get(`/gallery/albums/${slug}`).then(({ data }) => setD(data)).catch(() => setErr(true)); window.scrollTo(0, 0); }, [slug]);
  if (err) return <div className="py-32 text-center" data-testid="album-not-found"><p className="text-[#241019]/60 mb-4">This album could not be found.</p><Link to="/gallery" className="text-[#B4247E] font-semibold">Back to the gallery</Link></div>;
  if (!d) return <div className="py-32 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const { album: a, photos } = d;
  const items = photos.map((p) => ({ src: mediaSrc(p.url), caption: p.title, description: p.description }));
  return (
    <div data-testid="gallery-album-page">
      <section className="relative min-h-[460px] flex items-end overflow-hidden">
        {a.cover_url && <img src={mediaSrc(a.cover_url)} alt="" className="absolute inset-0 w-full h-full object-cover animate-[zoomIn_1.2s_ease]" />}
        <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, rgba(41,6,31,0.35) 0%, rgba(41,6,31,0.92) 100%)' }} />
        <div className="relative max-w-7xl mx-auto px-5 lg:px-8 w-full pb-14 pt-36">
          <Link to="/gallery" data-testid="album-back-link" className="text-[13px] font-semibold text-[#F7EFE9]/80 hover:text-[#CBA24B] flex items-center gap-1 mb-5"><ArrowLeft size={14} /> All albums</Link>
          <p className="eyebrow text-[#CBA24B] mb-3">{a.tag_type === 'program' ? 'Program' : a.tag_type === 'event' ? 'Event' : 'Album'}{a.date ? ` · ${new Date(`${a.date}T12:00:00`).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}` : ''} · {a.count} photo{a.count === 1 ? '' : 's'}</p>
          <h1 data-testid="album-title" className="font-serif text-4xl sm:text-5xl lg:text-6xl text-[#F7EFE9] font-semibold leading-tight max-w-3xl animate-[slideUp_.6s_ease]">{a.title}</h1>
        </div>
      </section>
      <section className="py-14 lg:py-20">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          {a.story && <p data-testid="album-story" className="max-w-3xl text-[16px] lg:text-[17px] leading-[1.85] text-[#241019]/75 whitespace-pre-line mb-12">{a.story}</p>}
          {items.length > 0 && <button data-testid="album-start-btn" onClick={() => setIdx(0)} className="btn-magenta rounded-full px-6 py-3 text-[14px] font-semibold flex items-center gap-2 mb-10"><Play size={15} /> View photos</button>}
          <div className="columns-1 sm:columns-2 lg:columns-3 gap-5 [&>*]:mb-5">
            {items.map((g, i) => (
              <Reveal key={photos[i].id} delay={(i % 3) * 80}>
                <button data-testid={`album-item-${i}`} onClick={() => setIdx(i)} className="block w-full img-zoom rounded-2xl overflow-hidden relative group">
                  <img src={g.src} alt={g.caption} className="w-full object-cover" />
                  {(g.caption || g.description) && (
                    <div className="absolute inset-0 flex flex-col justify-end p-5 opacity-0 group-hover:opacity-100 transition-opacity duration-300 text-left" style={{ background: 'linear-gradient(transparent 45%, rgba(41,6,31,0.85))' }}>
                      <p className="text-[#F7EFE9] text-[15px] font-semibold">{g.caption}</p>
                      {g.description && <p className="text-[#F7EFE9]/75 text-[12.5px] line-clamp-2 mt-1">{g.description}</p>}
                    </div>
                  )}
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
