import React from 'react';
import { board, executives, governance, org } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { ShieldCheck, FileCheck2 } from 'lucide-react';

function Avatar({ name }) {
  const initials = name.split(' ').filter(Boolean).slice(0, 2).map((n) => n[0]).join('');
  return (
    <div className="w-20 h-20 rounded-full flex items-center justify-center font-serif text-[24px] font-bold text-white shrink-0"
      style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)', boxShadow: '0 0 0 3px rgba(203,162,75,0.4)' }}>
      {initials}
    </div>
  );
}

export default function Leadership() {
  return (
    <div>
      <PageHero
        kicker="Governance & Oversight"
        title="Leadership Team & Board of Directors"
        subtitle="Our volunteer board and executive staff steward the mission with transparency, accountability, and the highest fiduciary standards."
      />

      {/* Board */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="max-w-2xl mb-12">
            <p className="eyebrow text-[#B4247E] mb-4">Board of Directors</p>
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">The women guiding our vision</h2>
            <p className="text-[#241019]/60 text-[13px] italic mt-3">Sample roster shown for demonstration purposes.</p>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-7">
            {board.map((m, i) => (
              <Reveal key={m.name} delay={(i % 3) * 100}>
                <div className="card-hover bg-white rounded-2xl p-7 h-full border border-[#3B0A2E]/8">
                  <div className="flex items-center gap-4 mb-5">
                    <Avatar name={m.name} />
                    <div>
                      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold leading-tight">{m.name}</h3>
                      <p className="text-[#B4247E] text-[13.5px] font-semibold mt-1">{m.role}</p>
                      <p className="text-[#241019]/55 text-[12.5px]">{m.affiliation}</p>
                    </div>
                  </div>
                  <p className="text-[#241019]/70 text-[14px] leading-relaxed">{m.bio}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Executives */}
      <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }}>
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="max-w-2xl mb-12">
            <p className="eyebrow text-[#B4247E] mb-4">Executive Staff</p>
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">Our operational leadership</h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-7 max-w-4xl">
            {executives.map((m, i) => (
              <Reveal key={m.name} delay={i * 100}>
                <div className="card-hover bg-white rounded-2xl p-7 flex items-center gap-5 border border-[#3B0A2E]/8">
                  <Avatar name={m.name} />
                  <div>
                    <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold">{m.name}</h3>
                    <p className="text-[#B4247E] text-[13.5px] font-semibold mb-2">{m.role}</p>
                    <p className="text-[#241019]/70 text-[14px] leading-relaxed">{m.bio}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* Governance policies */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="flex items-center gap-3 mb-12">
            <ShieldCheck className="text-[#B4247E]" size={30} />
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">Governance Policies</h2>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {governance.map((g, i) => (
              <Reveal key={g.title} delay={(i % 2) * 100}>
                <div className="card-hover rounded-2xl p-7 h-full flex gap-4" style={{ background: 'linear-gradient(160deg,#fff,#faf2f7)', border: '1px solid rgba(59,10,46,0.08)' }}>
                  <FileCheck2 className="text-[#CBA24B] shrink-0" size={24} />
                  <div>
                    <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-2">{g.title}</h3>
                    <p className="text-[#241019]/70 text-[14.5px] leading-relaxed">{g.desc}</p>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
