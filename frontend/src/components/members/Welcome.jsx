import React from 'react';
import { ClipboardList, Camera, Smartphone, ArrowRight, Heart } from 'lucide-react';

const STEPS = [
  { icon: ClipboardList, t: 'Finish your membership application', d: 'It takes about two minutes. Our team reviews every application personally.' },
  { icon: Camera, t: 'Add a photo to your profile', d: 'Once approved, open My Profile so your sisters can put a face to your name.' },
  { icon: Smartphone, t: 'Install the app on your phone', d: 'Add the portal to your home screen to get gathering reminders and news alerts.' },
];

export function Welcome({ me, onStart, onPortal }) {
  const first = (me.name || 'Sister').split(' ')[0];
  const active = me.status === 'active';
  return (
    <div data-testid="welcome-card" className="bg-white rounded-3xl p-7 sm:p-10 max-w-xl mx-auto" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
      <span className="w-14 h-14 rounded-2xl flex items-center justify-center mb-5" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Heart size={26} className="text-white" /></span>
      <p className="eyebrow text-[#B4247E] mb-2">Email confirmed</p>
      <h1 data-testid="welcome-title" className="font-serif text-[30px] sm:text-[34px] text-[#3B0A2E] font-semibold leading-tight">Welcome, {first}!</h1>
      <p data-testid="welcome-thanks" className="text-[#241019]/65 text-[14.5px] mt-2 mb-7">Thank you for joining Caring Sisters Club. We're so glad you're here. Here's what to do next:</p>
      <ol className="space-y-4 mb-8">
        {STEPS.map(({ icon: Icon, t, d }, i) => (
          <li key={t} data-testid={`welcome-step-${i + 1}`} className="flex gap-4" style={{ animation: `fadeUp .5s ease ${0.1 + i * 0.12}s both` }}>
            <span className="w-10 h-10 shrink-0 rounded-full bg-[#F7EFE9] text-[#B4247E] flex items-center justify-center"><Icon size={18} /></span>
            <span><span className="block text-[14.5px] font-semibold text-[#3B0A2E]">{i + 1}. {t}</span><span className="block text-[13px] text-[#241019]/60">{d}</span></span>
          </li>
        ))}
      </ol>
      <div className="flex flex-col sm:flex-row gap-3">
        {!active && <button data-testid="welcome-start-application-btn" onClick={onStart} className="btn-magenta rounded-full px-6 py-3.5 font-semibold flex items-center justify-center gap-2 flex-1">Start my application <ArrowRight size={16} /></button>}
        <button data-testid="welcome-go-portal-btn" onClick={onPortal} className={active ? 'btn-magenta rounded-full px-6 py-3.5 font-semibold flex-1' : 'rounded-full px-6 py-3.5 font-semibold border-2 border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] transition-colors'}>Go to the portal</button>
      </div>
    </div>
  );
}
