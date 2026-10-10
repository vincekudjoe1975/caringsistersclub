import React from 'react';
import { Quote } from 'lucide-react';
import { imgSrc } from '../lib/useHomeContent';

export const TestimonialCard = ({ t }) => (
  <div className="card-hover rounded-2xl p-8 h-full flex flex-col" style={{ background: 'linear-gradient(160deg,#fff,#faf2f7)', border: '1px solid rgba(59,10,46,0.08)' }} data-testid="testimonial-card">
    <Quote size={30} className="text-[#CBA24B] mb-4" />
    <p className="text-[#241019]/80 text-[15.5px] leading-relaxed italic mb-6 flex-1">&ldquo;{t.quote}&rdquo;</p>
    <div className="flex items-center gap-3">
      {t.photo_url && <img src={imgSrc(t.photo_url)} alt={t.name} className="w-12 h-12 rounded-full object-cover border-2 border-white shadow" />}
      <div>
        <p className="font-serif text-[#3B0A2E] font-semibold text-[17px]">{t.name}</p>
        {t.role && <p className="text-[#B4247E] text-[13px]">{t.role}</p>}
      </div>
    </div>
  </div>
);
