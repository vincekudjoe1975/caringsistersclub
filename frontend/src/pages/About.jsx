import React from 'react';
import { Link } from 'react-router-dom';
import { mission, values, story, org } from '../mock/mock';
import { useAboutContent, imgSrc } from '../lib/useHomeContent';

const FALLBACK = { hero_subtitle: 'What began as ten women around a kitchen table is now a global network transforming individual ambition into shared empowerment.', mission_title: 'Why we exist', mission_body: mission.body, mission_image: '', values, story_title: 'A journey of shared strength', story: story.map((s) => ({ ...s, image: '' })) };
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import * as Icons from 'lucide-react';
import { ArrowRight, BadgeCheck } from 'lucide-react';

export default function About() {
  const a = useAboutContent(FALLBACK);
  return (
    <div>
      <PageHero
        kicker="About Caring Sisters Club"
        title="A sisterhood built on love, respect, and empowerment"
        subtitle={a.hero_subtitle}
      />

      {/* Mission + 501c3 */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 grid lg:grid-cols-2 gap-14 items-center">
          <Reveal className="img-zoom rounded-[24px] overflow-hidden">
            <img src={imgSrc(a.mission_image, mission.image)} alt="Caring Sisters Club member" className="w-full h-[460px] object-cover" />
          </Reveal>
          <Reveal delay={120}>
            <p className="eyebrow text-[#B4247E] mb-4">Our Mission</p>
            <h2 className="font-serif text-[32px] lg:text-[42px] text-[#3B0A2E] font-semibold mb-6 leading-tight">{a.mission_title}</h2>
            <p className="text-[#241019]/75 text-[16px] leading-relaxed mb-5 whitespace-pre-line">{a.mission_body}</p>
            <div className="flex items-start gap-3 rounded-xl p-4" style={{ background: '#F7EFE9' }}>
              <BadgeCheck className="text-[#B4247E] shrink-0 mt-0.5" size={22} />
              <p className="text-[14px] text-[#3B0A2E]/85 leading-relaxed">
                {org.name} is a registered <strong>{org.status}</strong>. All contributions are tax-deductible to the extent permitted by law.
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Values */}
      <section className="py-20 lg:py-24" style={{ background: '#F7EFE9' }}>
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <p className="eyebrow text-[#B4247E] mb-4">Our Values</p>
            <h2 className="font-serif text-[32px] lg:text-[42px] text-[#3B0A2E] font-semibold">The principles that guide us</h2>
          </div>
          <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-7">
            {a.values.map((v, i) => {
              const Icon = Icons[v.icon] || Icons.Heart;
              return (
                <Reveal key={v.title} delay={i * 100}>
                  <div className="card-hover bg-white rounded-2xl p-7 h-full text-center border border-[#3B0A2E]/8">
                    <span className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-5" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                      <Icon size={24} className="text-white" />
                    </span>
                    <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-2">{v.title}</h3>
                    <p className="text-[#241019]/70 text-[14px] leading-relaxed">{v.text}</p>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* Story timeline */}
      <section className="py-20 lg:py-28">
        <div className="max-w-5xl mx-auto px-5 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-16">
            <p className="eyebrow text-[#B4247E] mb-4">Our Story</p>
            <h2 className="font-serif text-[32px] lg:text-[42px] text-[#3B0A2E] font-semibold">{a.story_title}</h2>
          </div>
          <div className="relative">
            <div className="absolute left-[19px] md:left-1/2 top-0 bottom-0 w-0.5 -translate-x-1/2" style={{ background: 'linear-gradient(#B4247E,#CBA24B)' }} />
            {a.story.map((s, i) => (
              <Reveal key={`${s.year}-${s.title}`} delay={i * 80}>
                <div className={`relative flex items-start gap-6 mb-12 md:w-1/2 ${i % 2 === 0 ? 'md:pr-12 md:ml-0' : 'md:pl-12 md:ml-auto md:flex-row-reverse md:text-right'}`}>
                  <span className="w-10 h-10 rounded-full flex items-center justify-center shrink-0 z-10 font-serif text-white text-[13px] font-bold" style={{ background: '#B4247E', boxShadow: '0 0 0 5px #F7EFE9' }}>
                    {i + 1}
                  </span>
                  <div className="card-hover bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 flex-1">
                    <span className="eyebrow text-[#CBA24B]">{s.year}</span>
                    <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mt-1 mb-2">{s.title}</h3>
                    <p className="text-[#241019]/70 text-[14.5px] leading-relaxed">{s.text}</p>
                    {s.image && <img src={imgSrc(s.image)} alt={s.title} className="mt-4 w-full h-40 object-cover rounded-xl" />}
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA strip */}
      <section className="csc-plum-bg py-14">
        <div className="max-w-5xl mx-auto px-5 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <h3 className="font-serif text-[#F7EFE9] text-[26px] md:text-[30px] font-semibold">Ready to build alongside us?</h3>
          <div className="flex gap-4">
            <Link to="/leadership" className="btn-outline-cream rounded-full px-7 py-3 font-semibold flex items-center gap-2">Meet our Board <ArrowRight size={16} /></Link>
            <Link to="/volunteer" className="btn-gold rounded-full px-7 py-3 font-semibold">Get Involved</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
