import React, { useState, useEffect } from 'react';
import { board as mockBoard, governance, org } from '../mock/mock';
import { api, mediaSrc } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { ShieldCheck, FileCheck2 } from 'lucide-react';

export default function Leadership() {
  const [board, setBoard] = useState(mockBoard);
  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/media?category=board');
        if (data && data.length) {
          const uploaded = data.map((d) => ({
            name: d.title || 'Team Member',
            role: d.subtitle || '',
            photo: mediaSrc(d.url),
            bio: '',
          }));
          setBoard([...mockBoard, ...uploaded]);
        }
      } catch (e) {
        /* fall back to mock */
      }
    })();
  }, []);
  return (
    <div>
      <PageHero
        kicker="Governance & Oversight"
        title="Executive & Leadership Team"
        subtitle="Meet the founders and board who steward our mission with transparency, accountability, and heart — guiding the sisterhood forward every day."
      />

      {/* Leadership Team */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="max-w-2xl mb-12">
            <p className="eyebrow text-[#B4247E] mb-4">Board of Directors</p>
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">The women guiding our vision</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-8">
            {board.map((m, i) => (
              <Reveal key={m.name} delay={(i % 3) * 100}>
                <div className="card-hover bg-white rounded-2xl overflow-hidden h-full border border-[#3B0A2E]/8">
                  <div className="img-zoom h-72 relative">
                    <img src={m.photo} alt={m.name} className="w-full h-full object-cover" style={{ objectPosition: 'center 20%' }} />
                    <div className="absolute inset-x-0 bottom-0 h-24" style={{ background: 'linear-gradient(transparent, rgba(41,6,31,0.55))' }} />
                  </div>
                  <div className="p-6">
                    <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold leading-tight">{m.name}</h3>
                    <p className="text-[#B4247E] text-[13.5px] font-semibold mt-1 mb-3">{m.role}</p>
                    <p className="text-[#241019]/70 text-[14px] leading-relaxed">{m.bio}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Governance policies */}
      <section className="py-20 lg:py-24" style={{ background: '#F7EFE9' }}>
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="flex items-center gap-3 mb-12">
            <ShieldCheck className="text-[#B4247E]" size={30} />
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">Governance Policies</h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {governance.map((g, i) => (
              <Reveal key={g.title} delay={(i % 2) * 100}>
                <div className="card-hover rounded-2xl p-7 h-full flex gap-4 bg-white" style={{ border: '1px solid rgba(59,10,46,0.08)' }}>
                  <FileCheck2 className="text-[#CBA24B] shrink-0" size={24} />
                  <div>
                    <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-2">{g.title}</h3>
                    <p className="text-[#241019]/70 text-[14.5px] leading-relaxed">{g.desc}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
          <p className="text-[#241019]/55 text-[13px] italic mt-8">
            {org.name} maintains formal governance policies in line with nonprofit best practices.
          </p>
        </div>
      </section>
    </div>
  );
}
