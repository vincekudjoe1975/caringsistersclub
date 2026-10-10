import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Printer } from 'lucide-react';

const money = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const KIND = { dues: 'Monthly dues', registration: 'Registration fees', fine: 'Attendance fines', birthday: 'Birthday contributions', bereavement: 'Bereavement support', illness: 'Serious illness support', other: 'Other' };
const METHOD = { cash: 'Cash', zelle: 'Zelle', check: 'Check', card: 'Card (online)', other: 'Other' };

const Section = ({ title, children }) => (
  <section className="mb-8"><p className="text-[11.5px] uppercase tracking-[0.2em] text-[#B4247E] font-semibold mb-2">{title}</p>{children}</section>
);
const Line = ({ l, v, bold, testid }) => (
  <div className={`flex justify-between py-1.5 border-b border-[#3B0A2E]/8 text-[14px] ${bold ? 'font-semibold text-[#3B0A2E]' : 'text-[#241019]/80'}`}><span>{l}</span><span data-testid={testid}>{v}</span></div>
);

export function TreasurerBody({ r }) {
  const kinds = Object.entries(r.money_in.by_kind).filter(([, v]) => v > 0);
  const methods = Object.entries(r.money_in.by_method).filter(([, v]) => v > 0);
  return (
    <div data-testid="treasurer-body">
      <div className="grid grid-cols-3 gap-3 mb-8 text-center">
        {[['Money in', r.money_in.total, 'tr-in'], ['Paid out', r.money_out.total, 'tr-out'], ['Still owed', r.outstanding.total, 'tr-owed']].map(([l, v, t]) => (
          <div key={l} className="rounded-xl bg-[#F7EFE9] py-4 print:border print:border-[#3B0A2E]/20"><p className="text-[12px] text-[#241019]/55">{l}</p><p data-testid={t} className="font-serif text-[24px] text-[#3B0A2E] font-semibold">{money(v)}</p></div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-x-10 print:grid-cols-2">
        <Section title="Collected by type">{kinds.length ? kinds.map(([k, v]) => <Line key={k} l={KIND[k]} v={money(v)} />) : <p className="text-[13px] text-[#241019]/50">No payments this month.</p>}<Line l="Total collected" v={money(r.money_in.total)} bold /></Section>
        <Section title="Collected by method">{methods.length ? methods.map(([k, v]) => <Line key={k} l={METHOD[k] || k} v={money(v)} />) : <p className="text-[13px] text-[#241019]/50">—</p>}<Line l={`${r.money_in.payments} payment${r.money_in.payments === 1 ? '' : 's'}`} v="" /></Section>
      </div>
      <Section title="Support funds (Sections 6.4 & 6.5)">
        {r.support.length ? r.support.map((s, i) => (
          <div key={i} className="flex justify-between py-1.5 border-b border-[#3B0A2E]/8 text-[14px] text-[#241019]/80"><span>{s.label}</span><span>in {money(s.collected)} · out {money(s.paid_out)}</span></div>
        )) : <p className="text-[13px] text-[#241019]/50">No support fund activity this month.</p>}
        <Line l="Total paid out" v={money(r.money_out.total)} bold />
      </Section>
      <Section title="Birthday collections (Section 6.3)">
        <Line l="Contributions requested this month" v={money(r.birthday.charged)} />
        <Line l="Contributions received this month" v={money(r.birthday.collected)} />
      </Section>
      <Section title="Outstanding balances">
        <Line l="Total still owed (current year)" v={money(r.outstanding.total)} />
        <Line l="Members with a balance" v={r.outstanding.members_owing} />
        <Line l="Members overdue" v={r.outstanding.overdue} />
      </Section>
      <Section title={`Year to date (${r.year})`}>
        <Line l="Money in" v={money(r.ytd.money_in)} testid="tr-ytd-in" />
        <Line l="Money out" v={money(r.ytd.money_out)} />
        <Line l="Net" v={money(r.ytd.net)} bold />
      </Section>
    </div>
  );
}

export default function TreasurerReport() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const [r, setR] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    const req = id ? api.get(`/members/treasurer-reports/${id}`) : api.get('/admin/members/treasurer', { params: { year: sp.get('year'), month: sp.get('month') } });
    req.then(({ data }) => setR(data)).catch((e) => setErr(e?.response?.status === 401 ? 'Please sign in to the member portal to view this report.' : e?.response?.data?.detail || 'Report not available.'));
  }, [id, sp]);
  if (err) return <p data-testid="treasurer-error" className="p-16 text-center text-[#241019]/70">{err}</p>;
  if (!r) return <p className="p-16 text-center text-[#241019]/50">Loading…</p>;
  return (
    <div className="min-h-screen bg-[#f3ece6] py-10 print:bg-white print:py-0">
      <div className="max-w-[820px] mx-auto mb-4 flex justify-end print:hidden">
        <button data-testid="treasurer-print-btn" onClick={() => window.print()} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Printer size={15} /> Print / Save as PDF</button>
      </div>
      <article data-testid="treasurer-report" className="max-w-[820px] mx-auto bg-white p-10 md:p-14 shadow-xl print:shadow-none print:p-0">
        <header className="text-center border-b-2 border-[#3B0A2E] pb-6 mb-8">
          <p className="font-serif text-[26px] text-[#3B0A2E] font-semibold tracking-wide">CARING SISTERS CLUB</p>
          <p className="text-[12px] uppercase tracking-[0.25em] text-[#B4247E] mt-1">Treasurer's Report</p>
          <p data-testid="treasurer-label" className="font-serif text-[20px] text-[#241019] mt-3">{r.label}</p>
        </header>
        <TreasurerBody r={r} />
        <div className="grid grid-cols-2 gap-10 mt-12">
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]">Treasurer</p></div>
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]">Financial Secretary</p></div>
        </div>
        <p className="text-[10.5px] text-[#241019]/40 mt-10">{r.shared_at ? `Shared with members ${new Date(r.shared_at).toLocaleDateString()}` : `Generated ${new Date(r.generated_at).toLocaleString()}`} · Amounts reflect payments recorded in the member portal.</p>
      </article>
    </div>
  );
}
