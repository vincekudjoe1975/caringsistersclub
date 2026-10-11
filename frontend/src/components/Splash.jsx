import React, { useEffect, useState } from 'react';
import logoImg from '../assets/team/logo.png';

const LINES = ['Welcome home, sister.', 'Together we rise.', 'Friendship. Growth. Giving.', 'So glad you are here.', 'Lifting each other, every day.'];
const standalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

export const Splash = () => {
  const [state, setState] = useState(() => {
    const forced = new URLSearchParams(window.location.search).has('splash');
    return (forced || standalone()) && !sessionStorage.getItem('csc_splash') ? 'show' : 'off';
  });
  const [line] = useState(() => LINES[Math.floor(Math.random() * LINES.length)]);
  useEffect(() => {
    if (state !== 'show') return undefined;
    sessionStorage.setItem('csc_splash', '1');
    const a = setTimeout(() => setState('fade'), 1500);
    const b = setTimeout(() => setState('off'), 2100);
    return () => { clearTimeout(a); clearTimeout(b); setState((v) => (v === 'show' ? v : 'off')); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (state === 'off') return null;
  return (
    <div data-testid="app-splash" onClick={() => setState('off')}
      className={`fixed inset-0 z-[200] csc-hero-gradient flex flex-col items-center justify-center text-center px-8 transition-opacity duration-500 ${state === 'fade' ? 'opacity-0' : 'opacity-100'}`}>
      <img src={logoImg} alt="Caring Sisters Club" className="w-28 h-28 rounded-full csc-splash-pop" style={{ boxShadow: '0 0 0 2px rgba(203,162,75,0.6), 0 0 48px -6px rgba(209,79,160,0.8)' }} />
      <h1 className="font-serif text-[#F7EFE9] text-3xl font-semibold mt-7 csc-splash-rise">Caring Sisters <span className="italic text-[#CBA24B] font-medium">Club</span></h1>
      <p data-testid="app-splash-line" className="text-[#F7EFE9]/80 text-base mt-3 csc-splash-rise" style={{ animationDelay: '0.25s' }}>{line}</p>
    </div>
  );
};
