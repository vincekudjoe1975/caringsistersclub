import React, { useState } from 'react';
import { api } from '../../lib/api';
import { Camera, BellRing, CalendarHeart, Sparkles } from 'lucide-react';

const TIPS = [
  { icon: Camera, t: 'Add your photo', d: 'Open My Profile so your sisters can put a face to your name.', tab: 'profile' },
  { icon: BellRing, t: 'Turn on phone alerts', d: 'In My Profile, on your phone, so you never miss a gathering.', tab: 'profile' },
  { icon: CalendarHeart, t: 'Check This Week', d: "See what's coming up: gatherings, birthdays, and votes.", tab: 'week' },
];

export function WelcomeBack({ me, onGo }) {
  const [open, setOpen] = useState(me.status === 'active' && me.welcome_seen === false);
  if (!open) return null;
  const close = (tab) => {
    api.post('/members/welcome-seen').catch(() => {});
    setOpen(false);
    if (tab) onGo(tab);
  };
  return (
    <div data-testid="welcome-back-overlay" className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-4 bg-[#1A0414]/60 backdrop-blur-sm" style={{ animation: 'fadeUp .35s ease both' }}>
      <div data-testid="welcome-back-card" role="dialog" aria-modal="true" aria-labelledby="welcome-back-title" className="bg-[#F7EFE9] rounded-3xl p-7 sm:p-9 w-full max-w-md" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.6)' }}>
        <span className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Sparkles size={22} className="text-white" /></span>
        <h2 id="welcome-back-title" data-testid="welcome-back-title" className="font-serif text-[28px] text-[#3B0A2E] font-semibold leading-tight">You're in, {(me.name || 'Sister').split(' ')[0]}!</h2>
        <p className="text-[14px] text-[#241019]/65 mt-1.5 mb-6">Welcome to the full member portal. Three quick tips to get started:</p>
        <ul className="space-y-2.5 mb-7">
          {TIPS.map(({ icon: Icon, t, d, tab }, i) => (
            <li key={t}>
              <button type="button" data-testid={`welcome-back-tip-${i + 1}`} onClick={() => close(tab)} className="w-full text-left flex gap-3.5 rounded-2xl bg-white p-3.5 border border-transparent hover:border-[#B4247E]/40 transition-colors" style={{ animation: `fadeUp .45s ease ${0.1 + i * 0.1}s both` }}>
                <span className="w-9 h-9 shrink-0 rounded-full bg-[#F7EFE9] text-[#B4247E] flex items-center justify-center"><Icon size={17} /></span>
                <span><span className="block text-[14px] font-semibold text-[#3B0A2E]">{t}</span><span className="block text-[12.5px] text-[#241019]/60">{d}</span></span>
              </button>
            </li>
          ))}
        </ul>
        <button data-testid="welcome-back-go-btn" onClick={() => close()} className="btn-magenta rounded-full w-full py-3.5 font-semibold">Let's go</button>
      </div>
    </div>
  );
}
