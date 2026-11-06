import React, { useState } from 'react';
import { api } from '../../lib/api';
import { PartyPopper, Megaphone, CalendarDays, MessagesSquare, UserCircle, ArrowRight } from 'lucide-react';

const STEPS = [
  { icon: Megaphone, tab: 'news', t: 'Announcements', d: 'Club news from the team lands here first.' },
  { icon: CalendarDays, tab: 'week', t: 'This Week', d: 'Gatherings, birthdays and votes coming up, all in one place.' },
  { icon: MessagesSquare, tab: 'talk', t: 'Discussion', d: 'Chat with your sisters, ask questions and share encouragement.' },
  { icon: UserCircle, tab: 'me', t: 'My Profile', d: 'Add your photo and turn on phone alerts so you never miss a thing.' },
];
const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;

export function AppCelebration({ me, onGo }) {
  const [open, setOpen] = useState(() => me.status === 'active' && me.welcome_seen !== false && !me.app_celebrated && isStandalone());
  const [step, setStep] = useState(-1);
  if (!open) return null;
  const close = (tab) => { api.post('/members/app-celebrated').catch(() => {}); setOpen(false); if (tab) onGo(tab); };
  const s = STEPS[step];
  return (
    <div data-testid="app-celebration-overlay" className="fixed inset-0 z-[80] flex items-end sm:items-center justify-center p-4 pb-[calc(env(safe-area-inset-bottom)+5rem)] sm:pb-4 bg-[#1A0414]/60 backdrop-blur-sm" style={{ animation: 'fadeUp .35s ease both' }}>
      <div data-testid="app-celebration-card" role="dialog" aria-modal="true" aria-labelledby="app-celebration-title" className="bg-[#F7EFE9] rounded-3xl p-7 sm:p-9 w-full max-w-md" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.6)' }}>
        {step < 0 ? (
          <>
            <span className="w-12 h-12 rounded-2xl flex items-center justify-center mb-4" style={{ background: 'linear-gradient(135deg,#CBA24B,#B4247E)' }}><PartyPopper size={22} className="text-white" /></span>
            <h2 id="app-celebration-title" data-testid="app-celebration-title" className="font-serif text-[28px] text-[#3B0A2E] font-semibold leading-tight">You're all set, {(me.name || 'Sister').split(' ')[0]}!</h2>
            <p className="text-[14px] text-[#241019]/65 mt-1.5 mb-7">The Club now lives on your home screen, one tap away. Want a 30-second look around?</p>
            <button data-testid="app-celebration-tour-btn" onClick={() => setStep(0)} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2">Show me around <ArrowRight size={16} /></button>
            <button data-testid="app-celebration-skip-btn" onClick={() => close()} className="w-full mt-3 py-2 text-[13.5px] font-semibold text-[#241019]/60 hover:text-[#3B0A2E]">Maybe later</button>
          </>
        ) : (
          <div key={step} style={{ animation: 'fadeUp .35s ease both' }}>
            <p data-testid="app-celebration-step-count" className="eyebrow text-[#B4247E] mb-3">Step {step + 1} of {STEPS.length}</p>
            <span className="w-12 h-12 rounded-2xl bg-white text-[#B4247E] flex items-center justify-center mb-4"><s.icon size={22} /></span>
            <h2 id="app-celebration-title" data-testid="app-celebration-step-title" className="font-serif text-[26px] text-[#3B0A2E] font-semibold leading-tight">{s.t}</h2>
            <p className="text-[14px] text-[#241019]/65 mt-1.5 mb-6">{s.d}</p>
            <div className="flex gap-1.5 mb-6">{STEPS.map((x, i) => <span key={x.tab} className={`h-1.5 flex-1 rounded-full transition-colors ${i <= step ? 'bg-[#B4247E]' : 'bg-[#3B0A2E]/10'}`} />)}</div>
            <div className="flex gap-2">
              <button data-testid="app-celebration-open-tab-btn" onClick={() => close(s.tab)} className="flex-1 rounded-full py-3 font-semibold text-[14px] border border-[#3B0A2E]/15 text-[#3B0A2E]">Go there</button>
              {step < STEPS.length - 1
                ? <button data-testid="app-celebration-next-btn" onClick={() => setStep(step + 1)} className="flex-1 btn-magenta rounded-full py-3 font-semibold text-[14px]">Next</button>
                : <button data-testid="app-celebration-done-btn" onClick={() => close()} className="flex-1 btn-magenta rounded-full py-3 font-semibold text-[14px]">Start exploring</button>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
