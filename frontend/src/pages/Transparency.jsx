import React, { useEffect, useState } from 'react';
import { org } from '../mock/mock';
import { api, mediaSrc } from '../lib/api';
import { useTransparency } from '../lib/useTransparency';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { FileText, Download, PieChart, TrendingUp, BarChart3 } from 'lucide-react';

const REPORT_GROUPS = [
  { type: '990', title: 'IRS Form 990 Filings', label: (r) => r.title || `Form 990 — Fiscal Year ${r.year}` },
  { type: 'annual', title: 'Annual Reports', label: (r) => r.title || `Annual Report ${r.year}` },
  { type: 'audit', title: 'Audited Financial Statements', label: (r) => r.title || `Audited Financials ${r.year}` },
  { type: 'other', title: 'Other Documents', label: (r) => r.title || `Document ${r.year}` },
];

const money = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;
const docHref = (url) => (url.startsWith('/api/') ? mediaSrc(url) : url);

function DocRow({ title, size, href }) {
  return (
    <div className="flex items-center justify-between py-4 px-5 rounded-xl bg-white border border-[#3B0A2E]/8 card-hover" data-testid="transparency-doc-row">
      <div className="flex items-center gap-3">
        <span className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ background: '#faf2f7' }}>
          <FileText size={20} className="text-[#B4247E]" />
        </span>
        <div>
          <p className="font-semibold text-[#3B0A2E] text-[15px]">{title}</p>
          <p className="text-[#241019]/50 text-[12.5px]">PDF{size ? <> &middot; {size}</> : null}</p>
        </div>
      </div>
      <a href={href} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-[#B4247E] font-semibold text-[13.5px] hover:text-[#D14FA0] transition-colors">
        <Download size={16} /> Download
      </a>
    </div>
  );
}

function SpendBreakdown({ breakdown, published }) {
  return (
    <Reveal>
      <div className="flex items-center gap-3 mb-6">
        <PieChart className="text-[#B4247E]" size={26} />
        <h2 className="font-serif text-[30px] lg:text-[38px] text-[#3B0A2E] font-semibold">How your gift is used</h2>
      </div>
      <p className="text-[#241019]/70 text-[15.5px] leading-relaxed mb-8">
        We are proud that the vast majority of every donation goes directly to programs serving women across the Diaspora.
        {!published && <span className="italic"> (Illustrative figures.)</span>}
      </p>
      <div className="space-y-5" data-testid="spend-breakdown">
        {breakdown.map((b, i) => (
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
  );
}

function FinancialsTable({ rows }) {
  if (!rows.length) return null;
  return (
    <section className="pb-20">
      <div className="max-w-5xl mx-auto px-5 lg:px-8">
        <div className="flex items-center gap-3 mb-6">
          <BarChart3 className="text-[#B4247E]" size={24} />
          <h3 className="font-serif text-[26px] text-[#3B0A2E] font-semibold">Financials by year</h3>
        </div>
        <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-x-auto">
          <table className="w-full text-left text-[14px]" data-testid="financials-table">
            <thead><tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide">
              <th className="px-6 py-4 font-semibold">Fiscal Year</th><th className="px-6 py-4 font-semibold text-right">Revenue</th>
              <th className="px-6 py-4 font-semibold text-right">Expenses</th><th className="px-6 py-4 font-semibold text-right">Program Spending</th>
            </tr></thead>
            <tbody>{rows.map((f) => (
              <tr key={f.year} className="border-t border-[#3B0A2E]/8">
                <td className="px-6 py-4 font-semibold text-[#3B0A2E]">{f.year}</td>
                <td className="px-6 py-4 text-right">{money(f.revenue)}</td>
                <td className="px-6 py-4 text-right">{money(f.expenses)}</td>
                <td className="px-6 py-4 text-right text-[#B4247E] font-semibold">
                  {money(f.program_expenses)}{f.expenses > 0 && <span className="text-[#241019]/50 font-normal"> ({Math.round((f.program_expenses / f.expenses) * 100)}%)</span>}
                </td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

export default function Transparency() {
  const t = useTransparency();
  const [uploaded, setUploaded] = useState([]);
  useEffect(() => {
    api.get('/media?category=document').then(({ data }) => setUploaded(data || []))
      .catch((e) => console.error('Transparency: failed to load documents', e));
  }, []);
  const published = !!t.updated_at;
  const reportUrls = new Set((t.reports || []).map((r) => r.url));
  const legacy = uploaded.filter((d) => !reportUrls.has(d.url));
  const groups = REPORT_GROUPS.map((g) => ({ ...g, items: (t.reports || []).filter((r) => r.type === g.type) })).filter((g) => g.items.length);
  const headline = t.breakdown?.[0]?.pct ?? 0;

  return (
    <div>
      <PageHero
        kicker="Financial Accountability"
        title="Transparency & Financial Reports"
        subtitle="We believe trust is earned. Access our IRS Form 990 filings, annual reports, and a breakdown of how every dollar is used."
      />

      <section className="py-20 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 grid lg:grid-cols-2 gap-14 items-center">
          <SpendBreakdown breakdown={t.breakdown || []} published={published} />
          <Reveal delay={140}>
            <div className="rounded-[24px] p-10 text-center" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }}>
              <TrendingUp className="text-[#CBA24B] mx-auto mb-4" size={40} />
              <p className="font-serif text-[#CBA24B] text-[72px] font-bold leading-none" data-testid="transparency-headline">{Math.round(headline)}&#162;</p>
              <p className="text-[#F7EFE9]/85 text-[16px] mt-4 max-w-xs mx-auto">{t.headline_text || 'of every dollar goes directly to programs and services for our sisters.'}</p>
              <div className="grid grid-cols-3 gap-3 mt-9">
                {(t.stats || []).slice(0, 3).map((s) => (
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

      <FinancialsTable rows={t.financials || []} />

      <section className="py-16 lg:py-20" style={{ background: '#F7EFE9' }}>
        <div className="max-w-5xl mx-auto px-5 lg:px-8">
          {groups.length === 0 && legacy.length === 0 ? (
            <p className="text-center text-[#241019]/60 text-[14.5px]" data-testid="reports-empty">Our Form 990 filings and annual reports will be published here. Contact us for a copy in the meantime.</p>
          ) : (
            <div className="grid md:grid-cols-2 gap-12">
              {groups.map((g) => (
                <div key={g.type}>
                  <h3 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-6">{g.title}</h3>
                  <div className="space-y-3">{g.items.map((r) => <DocRow key={r.id} title={g.label(r)} size={r.size} href={docHref(r.url)} />)}</div>
                </div>
              ))}
              {legacy.length > 0 && (
                <div>
                  <h3 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-6">Published Documents</h3>
                  <div className="space-y-3">{legacy.map((d) => (
                    <DocRow key={d.id} title={d.title || d.original_name} size={d.subtitle || `${(d.size / 1024).toFixed(0)} KB`} href={mediaSrc(d.url)} />
                  ))}</div>
                </div>
              )}
            </div>
          )}
          <p className="text-[#241019]/55 text-[13px] italic mt-10">{org.name} is a {org.status}.</p>
        </div>
      </section>
    </div>
  );
}
