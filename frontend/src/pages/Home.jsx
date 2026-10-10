import React from 'react';
import { Link } from 'react-router-dom';
import { hero } from '../mock/mock';
import { useHomeContent, imgSrc, DEFAULT_MISSION_IMAGE } from '../lib/useHomeContent';
import { TestimonialCard } from '../components/TestimonialCard';
import { useTransparency } from '../lib/useTransparency';
import { CtaLink } from './Initiatives';
import Reveal from '../components/Reveal';
import Marquee from '../components/Marquee';
import * as Icons from 'lucide-react';
import { ArrowRight, Quote, Heart } from 'lucide-react';

export default function Home() {
  const { stats: impactStats = [] } = useTransparency();
  const home = useHomeContent();
  return (
    <div>
      {/* HERO */}
      <section className="csc-hero-gradient relative overflow-hidden">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 pt-[120px] pb-16 lg:pt-[150px] lg:pb-24 grid lg:grid-cols-2 gap-12 items-center">
          <div className="relative z-10">
            <p className="eyebrow text-[#CBA24B] mb-5">{hero.kicker}</p>
            <h1 className="font-serif text-[#F7EFE9] text-[44px] sm:text-[56px] lg:text-[66px] leading-[1.02] font-semibold text-shadow-soft">
              {hero.title}
            </h1>
            <p className="text-[#F7EFE9]/80 text-[17px] lg:text-[19px] mt-6 max-w-xl leading-relaxed">
              {hero.subtitle}
            </p>
            <div className="flex flex-wrap items-center gap-4 mt-9">
              <Link to="/volunteer" className="btn-gold rounded-full px-8 py-3.5 font-semibold flex items-center gap-2">
                Join the Sisterhood <ArrowRight size={18} />
              </Link>
              <Link to="/donate" className="btn-outline-cream rounded-full px-8 py-3.5 font-semibold flex items-center gap-2">
                <Heart size={17} /> Donate
              </Link>
            </div>
          </div>
          <Reveal className="relative">
            <div className="relative rounded-[24px] overflow-hidden img-zoom" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.6)' }}>
              <img src={hero.image} alt="Confident professional woman of the Diaspora in a magenta blazer" className="w-full h-[420px] lg:h-[560px] object-cover" />
              <div className="absolute inset-0" style={{ background: 'linear-gradient(180deg, transparent 55%, rgba(41,6,31,0.55))' }} />
            </div>
            <div className="absolute -bottom-6 -left-6 bg-[#F7EFE9] rounded-2xl px-6 py-4 shadow-xl hidden md:block">
              <p className="font-serif text-[28px] text-[#3B0A2E] font-bold leading-none">2,400+</p>
              <p className="text-[12px] text-[#3B0A2E]/70 mt-1 tracking-wide">Sisters empowered</p>
            </div>
          </Reveal>
        </div>
      </section>

      <Marquee items={['EMPOWERMENT', 'NETWORKING', 'SISTERHOOD', 'PHILANTHROPY']} />

      {/* MISSION */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 grid lg:grid-cols-2 gap-14 items-center">
          <Reveal className="img-zoom rounded-[24px] overflow-hidden order-2 lg:order-1">
            <img src={imgSrc(home.mission_image, DEFAULT_MISSION_IMAGE)} alt="A member of the Caring Sisters Club smiling with confidence" className="w-full h-[440px] object-cover" />
          </Reveal>
          <Reveal delay={120} className="order-1 lg:order-2">
            <p className="eyebrow text-[#B4247E] mb-4">{home.mission_heading}</p>
            <h2 className="font-serif text-[34px] lg:text-[44px] leading-tight text-[#3B0A2E] font-semibold mb-6">
              {home.mission_title}
            </h2>
            <p className="text-[#241019]/75 text-[16px] leading-relaxed mb-6">{home.mission_body}</p>
            {home.mission_quote && (
              <blockquote className="border-l-4 pl-5 py-1 italic font-serif text-[19px] text-[#3B0A2E]" style={{ borderColor: '#CBA24B' }}>
                <Quote size={20} className="text-[#CBA24B] inline mr-1 -mt-2" />{home.mission_quote}
              </blockquote>
            )}
            <Link to="/about" className="inline-flex items-center gap-2 mt-8 text-[#B4247E] font-semibold link-underline">
              Discover Our Mission <ArrowRight size={17} />
            </Link>
          </Reveal>
        </div>
      </section>

      {/* PILLARS */}
      <section className="py-20 lg:py-24" style={{ background: '#F7EFE9' }}>
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <p className="eyebrow text-[#B4247E] mb-4">The Power of our Sisterhood</p>
            <h2 className="font-serif text-[34px] lg:text-[44px] text-[#3B0A2E] font-semibold">How we empower every sister</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-7">
            {home.pillars.map((p, i) => {
              const Icon = Icons[p.icon] || Icons.Sparkles;
              return (
                <Reveal key={p.title} delay={i * 120}>
                  <div className="card-hover bg-white rounded-2xl p-8 h-full border border-[#3B0A2E]/8">
                    <span className="w-14 h-14 rounded-xl flex items-center justify-center mb-6" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                      <Icon size={26} className="text-white" />
                    </span>
                    <h3 className="font-serif text-[23px] text-[#3B0A2E] font-semibold mb-3">{p.title}</h3>
                    <p className="text-[#241019]/70 text-[15px] leading-relaxed mb-6">{p.text}</p>
                    <CtaLink to={p.to} className="inline-flex items-center gap-2 text-[#B4247E] font-semibold text-[14px] link-underline">
                      {p.cta} <ArrowRight size={16} />
                    </CtaLink>
                  </div>
                </Reveal>
              );
            })}
          </div>
        </div>
      </section>

      {/* STATS */}
      <section className="csc-plum-bg py-16 lg:py-20">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 grid grid-cols-2 lg:grid-cols-4 gap-8">
          {impactStats.map((s, i) => (
            <Reveal key={s.label} delay={i * 100} className="text-center">
              <p className="font-serif text-[#CBA24B] text-[40px] lg:text-[52px] font-bold leading-none">{s.value}</p>
              <p className="text-[#F7EFE9]/75 text-[14px] mt-3 tracking-wide">{s.label}</p>
            </Reveal>
          ))}
        </div>
      </section>

      {/* TESTIMONIALS */}
      <section className="py-20 lg:py-28">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="text-center max-w-2xl mx-auto mb-14">
            <p className="eyebrow text-[#B4247E] mb-4">Voices of the Sisterhood</p>
            <h2 className="font-serif text-[34px] lg:text-[44px] text-[#3B0A2E] font-semibold">Stories of shared strength</h2>
          </div>
          <div className="grid md:grid-cols-3 gap-7">
            {home.testimonials.map((t, i) => (
              <Reveal key={t.id || t.name} delay={(i % 3) * 120}>
                <TestimonialCard t={t} />
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="csc-hero-gradient py-20 lg:py-24 relative overflow-hidden">
        <div className="absolute -right-20 -bottom-20 w-96 h-96 rounded-full opacity-25" style={{ background: 'radial-gradient(circle,#D14FA0,transparent 70%)' }} />
        <div className="max-w-3xl mx-auto px-5 lg:px-8 text-center relative">
          <h2 className="font-serif text-[#F7EFE9] text-[36px] lg:text-[48px] font-semibold leading-tight">
            Together, we transform vision into lasting change.
          </h2>
          <p className="text-[#F7EFE9]/75 text-[17px] mt-5 mb-9">
            Become a sister, volunteer your time, or give to fuel programs that uplift women across the Diaspora.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link to="/volunteer" className="btn-gold rounded-full px-8 py-3.5 font-semibold">Join the Sisterhood</Link>
            <Link to="/donate" className="btn-magenta rounded-full px-8 py-3.5 font-semibold">Make a Donation</Link>
          </div>
        </div>
      </section>
    </div>
  );
}
