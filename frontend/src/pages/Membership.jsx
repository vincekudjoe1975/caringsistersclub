import React from 'react';
import { Link } from 'react-router-dom';
import PageHero from '../components/PageHero';
import { Heart, Users, MapPin, HandCoins, CalendarCheck, LogIn, Sparkles } from 'lucide-react';

const VALUES = [
  { t: 'Love', d: 'Building sincere and genuine bonds of sisterhood and friendship.' },
  { t: 'Respect', d: 'Upholding integrity, honesty, trust, and empathy in all relationships.' },
  { t: 'Empowerment', d: 'Promoting self-worth, leadership, and productivity among women.' },
];

const REQS = [
  { icon: Users, t: 'Women 18 and older', d: 'Open to women aged eighteen and above who support our mission and values.' },
  { icon: MapPin, t: 'Delaware residents', d: 'Membership is currently open to residents of the State of Delaware.' },
  { icon: Heart, t: 'Referred by a sister', d: 'New members are nominated and sponsored by a current member in good standing.' },
  { icon: HandCoins, t: 'Registration & dues', d: 'A one-time $10 registration fee and $10 monthly dues keep membership active.' },
  { icon: CalendarCheck, t: 'Show up for each other', d: 'General meetings at least every two months, with in-person gatherings in April, August and December.' },
  { icon: Sparkles, t: 'Benefits of belonging', d: 'Members in good standing receive birthday celebrations and support during bereavement or serious illness.' },
];

const STEPS = ['Talk with the member who will refer you.', 'Sign in to the member portal with Google and complete the short application.', 'Our membership team reviews it and emails you once approved.'];

export default function Membership() {
  return (
    <>
      <PageHero kicker="Membership" title="Join the sisterhood" subtitle="Caring Sisters Club unites women from diverse backgrounds to uplift, support and inspire one another." />
      <section className="py-20 px-5" style={{ background: '#F7EFE9' }}>
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-5 mb-20" data-testid="membership-values">
            {VALUES.map((v) => (
              <div key={v.t} className="rounded-2xl p-7 bg-white border border-[#3B0A2E]/8">
                <p className="font-serif text-[26px] text-[#B4247E] font-semibold mb-2">{v.t}</p>
                <p className="text-[14.5px] text-[#241019]/75">{v.d}</p>
              </div>
            ))}
          </div>
          <p className="eyebrow text-[#B4247E] mb-3">Who can join</p>
          <h2 className="font-serif text-[34px] md:text-[42px] text-[#3B0A2E] font-semibold mb-10 max-w-2xl leading-tight">What membership looks like</h2>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5 mb-20" data-testid="membership-requirements">
            {REQS.map(({ icon: Icon, t, d }) => (
              <div key={t} className="rounded-2xl p-6 bg-white border border-[#3B0A2E]/8 hover:-translate-y-1 transition-transform duration-300">
                <span className="w-11 h-11 rounded-xl flex items-center justify-center mb-4" style={{ background: '#faf2f7' }}><Icon size={20} className="text-[#B4247E]" /></span>
                <p className="font-semibold text-[#3B0A2E] mb-1">{t}</p>
                <p className="text-[14px] text-[#241019]/70 leading-relaxed">{d}</p>
              </div>
            ))}
          </div>
          <div className="csc-plum-deep-bg rounded-3xl p-8 md:p-14 grid md:grid-cols-[1fr_auto] gap-10 items-center">
            <div>
              <h3 className="font-serif text-[30px] text-[#F7EFE9] font-semibold mb-6">How to join</h3>
              <ol className="space-y-4">
                {STEPS.map((s, i) => (
                  <li key={i} className="flex gap-4 text-[#F7EFE9]/85 text-[15px]"><span className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center font-semibold text-[#3B0A2E] bg-[#CBA24B]">{i + 1}</span>{s}</li>
                ))}
              </ol>
              <p className="text-[#F7EFE9]/55 text-[13px] mt-6">Our full bylaws are available to members inside the portal.</p>
            </div>
            <Link to="/members" data-testid="membership-apply-btn" className="btn-magenta rounded-full px-8 py-4 font-semibold flex items-center gap-2 justify-center"><LogIn size={18} /> Apply or sign in</Link>
          </div>
        </div>
      </section>
    </>
  );
}
