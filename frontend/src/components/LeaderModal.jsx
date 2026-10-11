import React, { useEffect, useState, useCallback, useRef } from 'react';
import { X, ChevronLeft, ChevronRight, Mail, Linkedin } from 'lucide-react';
import { mediaSrc } from '../lib/api';

export const leaderPhoto = (u) => (u && u.startsWith('/api/') ? mediaSrc(u) : u);
const initials = (n) => (n || '?').split(' ').map((x) => x[0]).slice(0, 2).join('').toUpperCase();

export function LeaderPhoto({ m, className = '' }) {
  return m.photo_url
    ? <img loading="lazy" decoding="async" src={leaderPhoto(m.photo_url)} alt={m.name} className={`w-full h-full object-cover ${className}`} style={{ objectPosition: 'center 20%' }} />
    : <div className={`w-full h-full flex items-center justify-center font-serif text-5xl text-white/80 ${className}`} style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>{initials(m.name)}</div>;
}

export function LeaderCard({ m, onOpen, testid }) {
  return (
    <button onClick={onOpen} data-testid={testid} className="group text-left w-full bg-white rounded-2xl overflow-hidden h-full border border-[#3B0A2E]/8 transition-[transform,box-shadow] duration-500 hover:-translate-y-1.5 hover:shadow-[0_30px_60px_-30px_rgba(59,10,46,0.45)] focus:outline-none focus-visible:ring-2 focus-visible:ring-[#B4247E]">
      <div className="h-72 relative overflow-hidden">
        <LeaderPhoto m={m} className="transition-transform duration-700 group-hover:scale-[1.06]" />
        <div className="absolute inset-0 flex flex-col justify-end p-5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" style={{ background: 'linear-gradient(transparent 30%, rgba(41,6,31,0.88))' }}>
          {m.intro && <p className="text-[#F7EFE9] text-[13.5px] leading-relaxed line-clamp-3 translate-y-3 group-hover:translate-y-0 transition-transform duration-500">{m.intro}</p>}
          <span className="mt-3 self-start text-[12px] font-semibold uppercase tracking-[0.2em] text-[#CBA24B] translate-y-3 group-hover:translate-y-0 transition-transform duration-500 delay-75">Read full bio →</span>
        </div>
      </div>
      <div className="p-6">
        <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold leading-tight">{m.name}</h3>
        <p className="text-[#B4247E] text-[13.5px] font-semibold mt-1">{m.role}</p>
        {m.intro && <p className="text-[#241019]/65 text-[14px] leading-relaxed mt-3 line-clamp-2 md:hidden">{m.intro}</p>}
        <p className="md:hidden text-[12px] font-semibold text-[#B4247E] mt-3">Tap to read bio</p>
      </div>
    </button>
  );
}

export function LeaderModal({ list, index, setIndex, onClose }) {
  const [shown, setShown] = useState(false);
  const startY = useRef(null);
  const [drag, setDrag] = useState(0);
  const m = list[index];
  const go = useCallback((d) => setIndex((i) => (i + d + list.length) % list.length), [list.length, setIndex]);
  const close = useCallback(() => { setShown(false); setTimeout(onClose, 280); }, [onClose]);
  useEffect(() => { requestAnimationFrame(() => setShown(true)); const o = document.body.style.overflow; document.body.style.overflow = 'hidden'; return () => { document.body.style.overflow = o; }; }, []);
  useEffect(() => {
    const k = (e) => { if (e.key === 'Escape') close(); else if (e.key === 'ArrowRight') go(1); else if (e.key === 'ArrowLeft') go(-1); };
    window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k);
  }, [go, close]);
  if (!m) return null;
  const bio = m.bio || m.intro || '';
  return (
    <div data-testid="leader-modal" role="dialog" aria-modal="true" aria-label={m.name} onClick={close}
      className={`fixed inset-0 z-[70] flex items-end md:items-center justify-center md:p-8 transition-[background-color,backdrop-filter] duration-300 ${shown ? 'bg-[#29061F]/75 backdrop-blur-[14px]' : 'bg-transparent'}`}>
      <div onClick={(e) => e.stopPropagation()}
        onTouchStart={(e) => { startY.current = e.touches[0].clientY; }}
        onTouchMove={(e) => { if (startY.current != null) setDrag(Math.max(0, e.touches[0].clientY - startY.current)); }}
        onTouchEnd={() => { if (drag > 110) close(); setDrag(0); startY.current = null; }}
        style={{ transform: shown ? `translateY(${drag}px)` : undefined }}
        className={`relative bg-white w-full md:max-w-4xl max-h-[92vh] md:max-h-[82vh] rounded-t-[28px] md:rounded-[28px] overflow-hidden flex flex-col md:flex-row shadow-[0_50px_100px_-30px_rgba(0,0,0,0.6)] transition-[transform,opacity] duration-300 ease-out ${shown ? 'opacity-100 md:scale-100' : 'opacity-0 translate-y-full md:translate-y-0 md:scale-90'}`}>
        <div className="md:hidden flex justify-center pt-3 pb-1 absolute inset-x-0 top-0 z-10"><span className="w-12 h-1.5 rounded-full bg-white/80" /></div>
        <div key={m.id || m.name} className="md:w-[42%] h-64 md:h-auto md:min-h-[440px] shrink-0 relative overflow-hidden animate-[fadeIn_.4s_ease]">
          <LeaderPhoto m={m} />
          <div className="absolute inset-x-0 bottom-0 h-28 md:hidden" style={{ background: 'linear-gradient(transparent, rgba(41,6,31,0.75))' }} />
          <div className="absolute bottom-4 left-5 md:hidden"><p className="font-serif text-white text-[24px] font-semibold leading-tight">{m.name}</p><p className="text-[#CBA24B] text-[13px] font-semibold">{m.role}</p></div>
        </div>
        <div key={`b-${m.id || m.name}`} className="flex-1 overflow-y-auto p-7 md:p-10 animate-[slideUp_.45s_ease]">
          <div className="hidden md:block">
            <p className="eyebrow text-[#CBA24B] mb-2">{m.group === 'executive' ? 'Executive Team' : 'Board of Directors'}</p>
            <h2 data-testid="leader-modal-name" className="font-serif text-[34px] text-[#3B0A2E] font-semibold leading-tight">{m.name}</h2>
            <p data-testid="leader-modal-role" className="text-[#B4247E] font-semibold text-[15px] mt-1 mb-6">{m.role}</p>
          </div>
          {m.quote && <blockquote data-testid="leader-modal-quote" className="font-serif italic text-[20px] leading-snug text-[#3B0A2E] border-l-4 border-[#CBA24B] pl-5 mb-6">“{m.quote}”</blockquote>}
          <div data-testid="leader-modal-bio" className="text-[15px] leading-[1.85] text-[#241019]/80 whitespace-pre-line">{bio || 'Biography coming soon.'}</div>
          {(m.email || m.linkedin) && (
            <div className="flex flex-wrap gap-3 mt-7">
              {m.email && <a data-testid="leader-modal-email" href={`mailto:${m.email}`} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] transition-colors flex items-center gap-1.5"><Mail size={14} /> Email</a>}
              {m.linkedin && <a data-testid="leader-modal-linkedin" href={m.linkedin} target="_blank" rel="noopener noreferrer" className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] transition-colors flex items-center gap-1.5"><Linkedin size={14} /> LinkedIn</a>}
            </div>
          )}
          {list.length > 1 && (
            <div className="flex items-center justify-between mt-9 pt-5 border-t border-[#3B0A2E]/8">
              <button data-testid="leader-modal-prev" onClick={() => go(-1)} className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] flex items-center gap-1 transition-colors"><ChevronLeft size={16} /> {list[(index - 1 + list.length) % list.length].name.split(' ')[0]}</button>
              <span className="text-[12px] text-[#241019]/45">{index + 1} / {list.length}</span>
              <button data-testid="leader-modal-next" onClick={() => go(1)} className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] flex items-center gap-1 transition-colors">{list[(index + 1) % list.length].name.split(' ')[0]} <ChevronRight size={16} /></button>
            </div>
          )}
        </div>
        <button data-testid="leader-modal-close" onClick={close} aria-label="Close" className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/90 md:bg-[#F7EFE9] text-[#3B0A2E] flex items-center justify-center hover:rotate-90 transition-transform duration-300 z-10"><X size={20} /></button>
      </div>
    </div>
  );
}
