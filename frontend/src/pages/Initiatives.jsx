import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { initiatives } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { ArrowRight } from 'lucide-react';

const categories = ['All', 'Professional', 'Philanthropy', 'Housing', 'Community'];

export default function Initiatives() {
  const [active, setActive] = useState('All');
  const filtered = active === 'All' ? initiatives : initiatives.filter((i) => i.category === active);

  return (
    <div>
      <PageHero
        kicker="Programs & Initiatives"
        title="Programs that turn vision into impact"
        subtitle="From business acceleration to housing support and community care, explore the initiatives powering our sisterhood."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8">
          <div className="flex flex-wrap gap-3 mb-12">
            {categories.map((c) => (
              <button
                key={c}
                onClick={() => setActive(c)}
                className={`px-5 py-2 rounded-full text-[14px] font-semibold transition-all ${
                  active === c ? 'text-white' : 'text-[#3B0A2E] hover:bg-[#f2e6ee]'
                }`}
                style={active === c ? { background: '#B4247E' } : { background: '#F7EFE9' }}
              >
                {c}
              </button>
            ))}
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-7">
            {filtered.map((item, i) => (
              <Reveal key={item.title} delay={(i % 3) * 100}>
                <div className="card-hover bg-white rounded-2xl overflow-hidden h-full border border-[#3B0A2E]/8">
                  <div className="img-zoom h-52">
                    <img src={item.image} alt={item.title} className="w-full h-full object-cover" />
                  </div>
                  <div className="p-7">
                    <span className="eyebrow text-[#CBA24B]">{item.category}</span>
                    <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mt-2 mb-3">{item.title}</h3>
                    <p className="text-[#241019]/70 text-[14.5px] leading-relaxed mb-5">{item.text}</p>
                    <Link to="/volunteer" className="inline-flex items-center gap-2 text-[#B4247E] font-semibold text-[14px] link-underline">
                      Get Involved <ArrowRight size={16} />
                    </Link>
                  </div>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      <section className="csc-plum-bg py-14">
        <div className="max-w-5xl mx-auto px-5 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-6">
          <h3 className="font-serif text-[#F7EFE9] text-[26px] md:text-[30px] font-semibold">Want to bring a program to your city?</h3>
          <Link to="/contact" className="btn-gold rounded-full px-8 py-3.5 font-semibold whitespace-nowrap">Start a Chapter</Link>
        </div>
      </section>
    </div>
  );
}
