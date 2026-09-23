import React from 'react';
import { financials, org, stats } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { FileText, Download, PieChart, TrendingUp } from 'lucide-react';

function DocRow({ title, size }) {
  return (
    <div className="flex items-center justify-between py-4 px-5 rounded-xl bg-white border border-[#3B0A2E]/8 card-hover">
      <div className="flex items-center gap-3">
        <span className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: '#faf2f7' }}>
          <FileText size={20} className="text-[#B4247E]" />
        </span>
        <div>
          <p className="font-semibold text-[#3B0A2E] text-[15px]">{title}</p>
          <p className="text-[#241019]/50 text-[12.5px]">PDF &middot; {size}</p>
        </div>
      </div>
      <button onClick={(e) => e.preventDefault()} className="flex items-center gap-2 text-[#B4247E] font-semibold text-[13.5px] hover:text-[#D14FA0] transition-colors">
        <Download size={16} /> Download
      </button>
    </div>
  );
}

export default function Transparency() {
  return (
    <div>
      <PageHero
        kicker="Financial Accountability"
        title="Transparency & Financial Reports"
        subtitle="We believe trust is earned. Access our IRS Form 990 filings, annual reports, and a breakdown of how every dollar is used."
      />

      {/* Spend breakdown */}
      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 grid lg:grid-cols-2 gap-14 items-center">
          <Reveal>
            <div className="flex items-center gap-3 mb-6">
              <PieChart className="text-[#B4247E]" size={26} />
              <h2 className="font-serif text-[30px] lg:text-[38px] text-[#3B0A2E] font-semibold">How your gift is used</h2>
            </div>
            <p className="text-[#241019]/70 text-[15.5px] leading-relaxed mb-8">
              We are proud that the vast majority of every donation goes directly to programs serving women across the Diaspora.
              <span className="italic"> (Illustrative figures for demonstration.)</span>
            </p>
            <div className="space-y-5">
              {financials.breakdown.map((b, i) => (
                <Reveal key={b.label} delay={i * 120}>
                  <div>
                    <div className="flex justify-between mb-2">
                      <span className="text-[#3B0A2E] font-semibold text-[14.5px]">{b.label}</span>
                      <span className="text-[#3B0A2E] font-bold text-[14.5px]">{b.pct}%</span>
                    </div>
                    <div className="h-3 rounded-full overflow-hidden" style={{ background: '#eadfe6' }}>
                      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${b.pct}%`, background: b.color }} />
                    </div>
                  </div>
                </Reveal>
              ))}
            </div>
          </Reveal>
          <Reveal delay={140}>
            <div className="rounded-[24px] p-10 text-center" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }}>
              <TrendingUp className="text-[#CBA24B] mx-auto mb-4" size={40} />
              <p className="font-serif text-[#CBA24B] text-[72px] font-bold leading-none">82&#162;</p>
              <p className="text-[#F7EFE9]/85 text-[16px] mt-4 max-w-xs mx-auto">of every dollar goes directly to programs and services for our sisters.</p>
              <div className="grid grid-cols-3 gap-3 mt-9">
                {stats.slice(0, 3).map((s) => (
                  <div key={s.label}>
                    <p className="font-serif text-[#F7EFE9] text-[22px] font-bold">{s.value}</p>
                    <p className="text-[#F7EFE9]/60 text-[11px] mt-1 leading-tight">{s.label}</p>
                  </div>
                ))}
              </div>
            </div>
          </Reveal>
        </div>
      </section>

      {/* Documents */}
      <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }}>
        <div className="max-w-5xl mx-auto px-5 lg:px-8 grid md:grid-cols-2 gap-12">
          <div>
            <h3 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-6">IRS Form 990 Filings</h3>
            <div className="space-y-3">
              {financials.form990.map((f) => (
                <DocRow key={f.year} title={`Form 990 — Fiscal Year ${f.year}`} size={f.size} />
              ))}
            </div>
          </div>
          <div>
            <h3 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-6">Annual Reports</h3>
            <div className="space-y-3">
              {financials.annualReports.map((f) => (
                <DocRow key={f.year} title={`Annual Report ${f.year}`} size={f.size} />
              ))}
            </div>
          </div>
        </div>
        <p className="max-w-5xl mx-auto px-5 lg:px-8 text-[#241019]/55 text-[13px] italic mt-8">
          Documents are sample placeholders for demonstration. {org.name} (EIN {org.ein}) is a {org.status}.
        </p>
      </section>
    </div>
  );
}
