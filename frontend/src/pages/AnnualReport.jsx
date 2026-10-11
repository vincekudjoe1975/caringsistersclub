import React, { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Printer } from 'lucide-react';

const money = (n) => `$${Number(n || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const KIND = { dues: 'Dues', registration: 'Registration', fine: 'Fines', birthday: 'Birthday', bereavement: 'Bereavement', illness: 'Serious illness', other: 'Other' };
const BKIND = { resolution: 'Resolution', amendment: 'Bylaw amendment', election: 'Election' };
const H = ({ children }) => <h2 className="text-[12px] uppercase tracking-[0.2em] text-[#B4247E] font-semibold mt-9 mb-3 border-b border-[#3B0A2E]/15 pb-1">{children}</h2>;
const Stat = ({ l, v, testid }) => <div className="rounded-xl bg-[#F7EFE9] py-3 text-center print:border print:border-[#3B0A2E]/20"><p className="text-[11.5px] text-[#241019]/55">{l}</p><p data-testid={testid} className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{v}</p></div>;

export function AnnualBody({ r }) {
  const a = r.attendance;
  return (
    <div data-testid="annual-body" className="text-[13.5px]">
      <H>Membership</H>
      <div className="grid grid-cols-3 gap-3"><Stat l="Active members" v={r.membership.active} testid="an-active" /><Stat l="Joined this year" v={r.membership.joined} /><Stat l="Left this year" v={r.membership.ended} /></div>
      {r.membership.officers.length > 0 && <p className="mt-3 text-[#241019]/75"><b>Officers:</b> {r.membership.officers.map((o) => `${o.office}: ${o.name}`).join(' · ')}</p>}
      <H>Attendance</H>
      <div className="grid grid-cols-4 gap-3 mb-3"><Stat l="Meetings held" v={a.meetings.length} testid="an-meetings" /><Stat l="Avg attendance" v={`${a.average_rate}%`} /><Stat l="Warnings" v={a.warnings} /><Stat l="Fines" v={a.fines} /></div>
      <table className="w-full"><tbody>{a.meetings.map((m, i) => <tr key={i} className="border-b border-[#3B0A2E]/8"><td className="py-1.5">{new Date(m.date + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })} · {m.title}</td><td className="text-right">{m.present} present · {m.absent} absent · {m.excused} excused</td><td className="text-right w-14 font-semibold">{m.rate}%</td></tr>)}</tbody></table>
      {(a.terminations > 0 || a.officer_removals > 0) && <p className="mt-2 text-[#241019]/70">{a.terminations} member(s) reached 4+ absences; {a.officer_removals} officer(s) reached 3 absences.</p>}
      <H>Dues & finances</H>
      <div className="grid grid-cols-4 gap-3 mb-3"><Stat l="Dues expected" v={money(r.dues.expected)} /><Stat l="Collected (all)" v={money(r.dues.collected)} testid="an-collected" /><Stat l="Outstanding" v={money(r.dues.outstanding)} /><Stat l="Paid in full" v={`${r.dues.paid_in_full}/${r.dues.members}`} /></div>
      <p className="text-[#241019]/75"><b>By type:</b> {Object.entries(r.dues.by_kind).map(([k, v]) => `${KIND[k] || k} ${money(v)}`).join(' · ') || '—'}</p>
      <p className="text-[#241019]/75 mt-1"><b>By method:</b> {Object.entries(r.dues.by_method).map(([k, v]) => `${k} ${money(v)}`).join(' · ') || '—'}</p>
      <H>Support funds</H>
      {r.support.length ? <table className="w-full"><tbody>{r.support.map((s, i) => <tr key={i} className="border-b border-[#3B0A2E]/8"><td className="py-1.5">{s.kind === 'bereavement' ? 'Bereavement' : 'Serious illness'}: {s.beneficiary}{s.relationship ? ` (${s.relationship})` : ''}</td><td className="text-right">expected {money(s.expected)} · collected {money(s.collected)} · paid out {money(s.paid_out)}</td></tr>)}</tbody></table> : <p className="text-[#241019]/50">No support collections this year.</p>}
      <H>Votes & elections</H>
      {r.votes.length ? <table className="w-full" data-testid="an-votes"><tbody>{r.votes.map((v, i) => {
        const res = v.results;
        const outcome = v.kind === 'election' ? (res.winner ? `${res.winner} elected` : 'No winner') : res.passed ? 'Adopted' : 'Not adopted';
        const tally = v.kind === 'election' ? v.candidates.map((c) => `${c.name} ${res.counts[c.user_id] || 0}`).join(', ') + `, abstain ${res.counts.abstain || 0}` : `Yes ${res.yes} · No ${res.no} · Abstain ${res.abstain}`;
        return <tr key={i} className="border-b border-[#3B0A2E]/8 align-top"><td className="py-1.5"><b>{v.title}</b><br /><span className="text-[#241019]/55">{BKIND[v.kind]}{v.position ? `: ${v.position}` : ''}</span></td><td className="text-right">{tally}<br /><span className="text-[#241019]/55">{res.voters}/{res.eligible} voted · quorum {res.quorum_met ? 'met' : 'not met'}</span></td><td className="text-right w-28 font-semibold">{outcome}</td></tr>;
      })}</tbody></table> : <p className="text-[#241019]/50">No votes closed this year.</p>}
    </div>
  );
}

export default function AnnualReport() {
  const { id } = useParams();
  const [sp] = useSearchParams();
  const [r, setR] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => {
    const req = id ? api.get(`/members/annual-reports/${id}`) : api.get('/admin/members/annual', { params: { year: sp.get('year') } });
    req.then(({ data }) => setR(data)).catch((e) => setErr(e?.response?.status === 401 ? 'Please sign in to the member portal to view this report.' : e?.response?.data?.detail || 'Report not available.'));
  }, [id, sp]);
  if (err) return <p data-testid="annual-error" className="p-16 text-center text-[#241019]/70">{err}</p>;
  if (!r) return <p className="p-16 text-center text-[#241019]/50">Loading…</p>;
  return (
    <div className="min-h-screen bg-[#f3ece6] py-10 print:bg-white print:py-0">
      <div className="max-w-[860px] mx-auto mb-4 flex justify-end print:hidden">
        <button data-testid="annual-print-btn" onClick={() => window.print()} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Printer size={15} /> Print / Save as PDF</button>
      </div>
      <article data-testid="annual-report" className="max-w-[860px] mx-auto bg-white p-10 md:p-14 shadow-xl print:shadow-none print:p-0">
        <header className="text-center border-b-2 border-[#3B0A2E] pb-6">
          <p className="font-serif text-[26px] text-[#3B0A2E] font-semibold tracking-wide">CARING SISTERS CLUB</p>
          <p className="text-[12px] uppercase tracking-[0.25em] text-[#B4247E] mt-1">Annual Summary for the Annual Meeting</p>
          <p data-testid="annual-year" className="font-serif text-[22px] text-[#241019] mt-3">{r.year}</p>
        </header>
        <AnnualBody r={r} />
        <div className="grid grid-cols-2 gap-10 mt-14">
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]">President</p></div>
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]">Secretary</p></div>
        </div>
        <p className="text-[10.5px] text-[#241019]/40 mt-10">{r.shared_at ? `Shared with members ${new Date(r.shared_at).toLocaleDateString()}` : `Generated ${new Date(r.generated_at).toLocaleString()}`}</p>
      </article>
    </div>
  );
}
