import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import { Heart, Maximize } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';
import logoImg from '../assets/team/logo.png';

const fmt = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

export default function GalaScreen() {
  const { eid } = useParams();
  const [d, setD] = useState(null);
  useEffect(() => {
    let alive = true;
    const load = () => api.get(`/gala/${eid}`).then(({ data }) => alive && setD(data)).catch(() => alive && setD((p) => p || false));
    load();
    const t = setInterval(load, 5000);
    return () => { alive = false; clearInterval(t); };
  }, [eid]);
  if (d === false) return <p className="p-10 text-center">Event not found.</p>;
  if (!d) return <div className="min-h-screen csc-hero-gradient" />;
  const pct = d.goal ? Math.min(100, Math.round((d.raised / d.goal) * 100)) : 0;
  const giveUrl = `${window.location.origin}/donate?gala=${eid}`;
  return (
    <div data-testid="gala-screen" className="min-h-screen csc-hero-gradient text-[#F7EFE9] p-6 lg:p-12 flex flex-col">
      <div className="flex items-center gap-4">
        <img src={logoImg} alt="" className="w-14 h-14 rounded-full" />
        <p className="font-serif text-2xl lg:text-3xl font-semibold">{d.title}</p>
        <button data-testid="gala-fullscreen" onClick={() => document.documentElement.requestFullscreen?.()} aria-label="Full screen" className="ml-auto w-11 h-11 rounded-full border border-white/20 flex items-center justify-center hover:bg-white/10"><Maximize size={18} /></button>
      </div>
      {d.paddle?.level && (
        <div data-testid="gala-paddle" className="mt-6 rounded-[32px] bg-[#CBA24B] text-[#3B0A2E] px-8 py-6 flex flex-wrap items-center gap-x-10 gap-y-3 csc-splash-pop">
          <p data-testid="gala-paddle-level" className="font-serif font-bold text-[56px] lg:text-[96px] leading-none">{fmt(d.paddle.level)} hands!</p>
          <p data-testid="gala-paddle-count" className="text-2xl lg:text-4xl font-bold">{(d.paddle.tally.find((t) => t.level === d.paddle.level) || { count: 0 }).count} paddles</p>
          <div className="flex flex-wrap gap-2 ml-auto">{d.paddle.tally.map((t) => <span key={t.level} className="rounded-full bg-[#3B0A2E]/10 px-4 py-1.5 text-lg font-semibold">{fmt(t.level)} × {t.count}</span>)}</div>
        </div>
      )}
      <div className="flex-1 grid lg:grid-cols-[1fr_auto] gap-10 lg:gap-16 items-center mt-8">
        <div className="min-w-0">
          <p className="uppercase tracking-[0.3em] text-[#CBA24B] text-sm lg:text-base font-semibold">Tonight we've raised</p>
          <p data-testid="gala-raised" className="font-serif font-bold leading-none mt-3 text-[64px] sm:text-[96px] lg:text-[140px] transition-all">{fmt(d.raised)}</p>
          {d.goal > 0 && <p data-testid="gala-goal" className="text-xl lg:text-3xl text-[#F7EFE9]/80 mt-3">of our {fmt(d.goal)} goal · {d.count} gift{d.count === 1 ? '' : 's'}</p>}
          <div className="h-10 lg:h-14 rounded-full bg-white/10 border border-white/15 overflow-hidden mt-8" role="progressbar" aria-valuenow={pct}>
            <div data-testid="gala-bar" className="h-full rounded-full flex items-center justify-end pr-4 transition-[width] duration-[1500ms] ease-out" style={{ width: `${Math.max(pct, 4)}%`, background: 'linear-gradient(90deg,#B4247E,#D14FA0,#CBA24B)' }}>
              <span className="font-bold text-white text-lg lg:text-2xl">{d.goal ? `${pct}%` : ''}</span>
            </div>
          </div>
          <div data-testid="gala-recent" className="mt-10 flex flex-wrap gap-3 min-h-[56px]">
            {d.recent.map((r, i) => (
              <span key={`${r.at}${i}`} className="rounded-full bg-white/10 border border-white/15 px-5 py-2.5 text-lg lg:text-xl flex items-center gap-2 csc-splash-rise" style={{ animationDelay: `${i * 60}ms` }}><Heart size={16} className="text-[#D14FA0] fill-[#D14FA0]" /> {r.name}</span>
            ))}
          </div>
        </div>
        <div className="bg-white rounded-[28px] p-6 lg:p-8 text-center text-[#3B0A2E] justify-self-center">
          <QRCodeSVG data-testid="gala-qr" value={giveUrl} size={260} fgColor="#3B0A2E" />
          <p className="font-serif text-2xl font-semibold mt-4">Scan to give</p>
          <p className="text-sm text-[#241019]/60 mt-1">Every gift lights up this screen</p>
          {d.auction && <div data-testid="gala-auction-qr" className="mt-5 pt-4 border-t border-[#3B0A2E]/10"><QRCodeSVG value={`${window.location.origin}/auction/${eid}`} size={110} fgColor="#B4247E" className="mx-auto" /><p className="text-sm font-semibold mt-2">Silent auction: scan to bid</p></div>}
        </div>
      </div>
      {d.sponsors?.length > 0 && (
        <div data-testid="gala-sponsors" className="mt-8 overflow-hidden rounded-2xl bg-white/95 py-3">
          <div className="flex items-center gap-12 w-max csc-marquee">
            {[...d.sponsors, ...d.sponsors].map((s, i) => <img key={i} src={mediaSrc(s.logo)} alt={s.name} className="h-14 lg:h-16 w-auto max-w-[200px] object-contain" />)}
          </div>
        </div>
      )}
    </div>
  );
}
