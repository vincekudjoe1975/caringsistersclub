import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { api } from '../lib/api';
import { LeaderPhoto, LeaderModal } from './LeaderModal';
import { DEFAULT_LEADERS } from '../pages/Leadership';

export function LeaderStrip() {
  const [team, setTeam] = useState([]);
  const [open, setOpen] = useState(null);
  const [paused, setPaused] = useState(false);
  useEffect(() => { api.get('/leaders').then(({ data }) => setTeam(data.items.length ? data.items : DEFAULT_LEADERS)).catch(() => setTeam(DEFAULT_LEADERS)); }, []);
  if (!team.length) return null;
  const loop = team.length < 8 ? [...team, ...team, ...team, ...team] : [...team, ...team];
  return (
    <section className="py-20 lg:py-24 overflow-hidden" style={{ background: '#F7EFE9' }} data-testid="leader-strip">
      <div className="max-w-7xl mx-auto px-5 lg:px-8 flex flex-wrap items-end justify-between gap-4 mb-12">
        <div>
          <p className="eyebrow text-[#B4247E] mb-4">Meet our leaders</p>
          <h2 className="font-serif text-[34px] lg:text-[44px] text-[#3B0A2E] font-semibold leading-tight">The women behind the sisterhood</h2>
        </div>
        <Link to="/leadership" data-testid="leader-strip-all" className="inline-flex items-center gap-2 text-[#B4247E] font-semibold text-[14px] link-underline">Meet the full team <ArrowRight size={16} /></Link>
      </div>
      <div className="relative" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onTouchStart={() => setPaused(true)} onTouchEnd={() => setTimeout(() => setPaused(false), 2500)}>
        <div className="absolute inset-y-0 left-0 w-16 lg:w-32 z-10 pointer-events-none" style={{ background: 'linear-gradient(90deg,#F7EFE9,transparent)' }} />
        <div className="absolute inset-y-0 right-0 w-16 lg:w-32 z-10 pointer-events-none" style={{ background: 'linear-gradient(270deg,#F7EFE9,transparent)' }} />
        <div className="csc-marquee-track gap-10 px-5" style={{ animationDuration: `${Math.max(30, loop.length * 4)}s`, animationPlayState: paused ? 'paused' : 'running' }}>
          {loop.map((m, i) => (
            <button key={`${m.id}-${i}`} data-testid={i < team.length ? `leader-strip-item-${i}` : undefined} onClick={() => setOpen(i % team.length)} className="group shrink-0 w-52 text-center whitespace-normal focus:outline-none">
              <div className="w-36 h-36 mx-auto rounded-full overflow-hidden p-1 transition-transform duration-500 group-hover:scale-105" style={{ background: 'linear-gradient(135deg,#CBA24B,#B4247E)' }}>
                <div className="w-full h-full rounded-full overflow-hidden"><LeaderPhoto m={m} className="transition-transform duration-700 group-hover:scale-110" /></div>
              </div>
              <p className="font-serif text-[18px] text-[#3B0A2E] font-semibold mt-4 leading-tight">{m.name}</p>
              <p className="text-[12.5px] text-[#B4247E] font-semibold mt-1">{m.role}</p>
              {m.quote && <p data-testid={i < team.length ? `leader-strip-quote-${i}` : undefined} className="font-serif italic text-[13.5px] text-[#241019]/70 mt-2 line-clamp-3 leading-snug">“{m.quote}”</p>}
              <span className="text-[11px] uppercase tracking-[0.2em] text-[#241019]/45 opacity-0 group-hover:opacity-100 transition-opacity">Read bio</span>
            </button>
          ))}
        </div>
      </div>
      {open !== null && <LeaderModal list={team} index={open} setIndex={setOpen} onClose={() => setOpen(null)} />}
    </section>
  );
}
