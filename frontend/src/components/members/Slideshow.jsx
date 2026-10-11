import React, { useEffect, useState, useCallback, useRef } from 'react';
import { ChevronLeft, ChevronRight, Pause, Play, X, Maximize } from 'lucide-react';

const full = (u) => `${process.env.REACT_APP_BACKEND_URL}${u}`;

export function Slideshow({ photos, title, onClose }) {
  const [i, setI] = useState(0);
  const [playing, setPlaying] = useState(true);
  const ref = useRef(null);
  const n = photos.length;
  const go = useCallback((d) => setI((x) => (x + d + n) % n), [n]);
  useEffect(() => { if (!playing || n < 2) return undefined; const t = setTimeout(() => go(1), 6000); return () => clearTimeout(t); }, [i, playing, go, n]);
  useEffect(() => {
    const k = (e) => {
      if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1);
      else if (e.key === ' ') { e.preventDefault(); setPlaying((p) => !p); } else if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', k);
    return () => window.removeEventListener('keydown', k);
  }, [go, onClose]);
  useEffect(() => { ref.current?.requestFullscreen?.().catch(() => {}); return () => { if (document.fullscreenElement) document.exitFullscreen().catch(() => {}); }; }, []);
  if (!n) return null;
  const p = photos[i];
  return (
    <div ref={ref} data-testid="slideshow" className="fixed inset-0 z-[60] bg-black select-none">
      {photos.map((x, j) => (
        <img loading="lazy" decoding="async" key={x.id} src={full(x.url)} alt={x.caption || ''} className="absolute inset-0 w-full h-full object-contain transition-opacity duration-1000" style={{ opacity: j === i ? 1 : 0 }} />
      ))}
      <button data-testid="slideshow-prev-zone" aria-label="Previous" onClick={() => go(-1)} className="absolute inset-y-0 left-0 w-1/3" />
      <button data-testid="slideshow-next-zone" aria-label="Next" onClick={() => go(1)} className="absolute inset-y-0 right-0 w-1/3" />
      <div className="absolute inset-x-0 bottom-0 p-6 md:p-10 bg-gradient-to-t from-black/80 to-transparent text-white pointer-events-none">
        <p className="text-[12px] uppercase tracking-[0.25em] text-[#CBA24B]">{p.gathering_title || title}</p>
        {p.caption && <p data-testid="slideshow-caption" className="font-serif text-2xl md:text-3xl mt-1">{p.caption}</p>}
        <p className="text-[12.5px] text-white/60 mt-1">Shared by {p.uploader_name} · <span data-testid="slideshow-index">{i + 1}</span> / {n}</p>
      </div>
      <div className="absolute top-4 right-4 flex gap-2">
        <button data-testid="slideshow-prev" onClick={() => go(-1)} className="w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center hover:bg-white/25 transition-colors"><ChevronLeft size={20} /></button>
        <button data-testid="slideshow-toggle" onClick={() => setPlaying(!playing)} className="w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center hover:bg-white/25 transition-colors">{playing ? <Pause size={18} /> : <Play size={18} />}</button>
        <button data-testid="slideshow-next" onClick={() => go(1)} className="w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center hover:bg-white/25 transition-colors"><ChevronRight size={20} /></button>
        <button data-testid="slideshow-fullscreen" onClick={() => ref.current?.requestFullscreen?.().catch(() => {})} className="w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center hover:bg-white/25 transition-colors"><Maximize size={16} /></button>
        <button data-testid="slideshow-close" onClick={onClose} className="w-10 h-10 rounded-full bg-white/15 text-white flex items-center justify-center hover:bg-white/25 transition-colors"><X size={20} /></button>
      </div>
    </div>
  );
}
