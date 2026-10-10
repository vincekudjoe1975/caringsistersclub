import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../lib/api';
import { Printer } from 'lucide-react';

const KIND = { resolution: 'Resolution', amendment: 'Bylaw Amendment', election: 'Election' };
const dt = (iso) => new Date(iso).toLocaleString('en-US', { timeZone: 'America/New_York', dateStyle: 'long', timeStyle: 'short' });

const Row = ({ l, v, testid }) => (
  <tr className="border-b border-[#3B0A2E]/10"><td className="py-2 pr-6 text-[#241019]/60">{l}</td><td data-testid={testid} className="py-2 font-semibold text-[#241019]">{v}</td></tr>
);

export default function VoteRecord() {
  const { id } = useParams();
  const [b, setB] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get(`/members/ballots/${id}/record`).then(({ data }) => setB(data)).catch((e) => setErr(e?.response?.status === 401 ? 'Please sign in to the member portal to view this record.' : e?.response?.data?.detail || 'Record not available.')); }, [id]);
  if (err) return <p data-testid="record-error" className="p-16 text-center text-[#241019]/70">{err}</p>;
  if (!b) return <p className="p-16 text-center text-[#241019]/50">Loading…</p>;
  const r = b.results;
  const tally = b.kind === 'election'
    ? [...b.candidates.map((c) => [c.name, r.counts[c.user_id] || 0]), ['Abstentions', r.counts.abstain || 0]]
    : [['Yeas', r.yes], ['Nays', r.no], ['Abstentions', r.abstain]];
  const outcome = b.kind === 'election' ? (r.winner ? `${r.winner} elected ${b.position}` : r.tie ? 'Tie (no winner declared)' : 'No winner declared') : r.passed ? 'ADOPTED' : 'NOT ADOPTED';
  return (
    <div className="min-h-screen bg-[#f3ece6] py-10 print:bg-white print:py-0">
      <div className="max-w-[780px] mx-auto mb-4 flex justify-end print:hidden">
        <button data-testid="record-print-btn" onClick={() => window.print()} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Printer size={15} /> Print / Save as PDF</button>
      </div>
      <article data-testid="vote-record" className="max-w-[780px] mx-auto bg-white p-12 md:p-16 shadow-xl print:shadow-none print:p-0 text-[14px]">
        <header className="text-center border-b-2 border-[#3B0A2E] pb-6 mb-8">
          <p className="font-serif text-[26px] text-[#3B0A2E] font-semibold tracking-wide">CARING SISTERS CLUB</p>
          <p className="text-[12px] uppercase tracking-[0.25em] text-[#B4247E] mt-1">Official Record of Vote</p>
        </header>
        <h1 data-testid="record-title" className="font-serif text-[22px] text-[#241019] font-semibold mb-1">{b.title}</h1>
        <p className="text-[#241019]/60 mb-6">{KIND[b.kind]}{b.position ? `: ${b.position}` : ''}</p>
        {b.description && <p className="whitespace-pre-line text-[#241019]/85 mb-8 leading-relaxed border-l-2 border-[#CBA24B] pl-4">{b.description}</p>}
        <table className="w-full mb-8"><tbody>
          <Row l="Voting opened" v={dt(b.opens_at)} />
          <Row l="Voting closed" v={dt(b.closed_at || b.closes_at)} />
          <Row l="Members in good standing" v={r.eligible} testid="record-eligible" />
          <Row l="Ballots cast" v={r.voters} testid="record-voters" />
          <Row l="Quorum (simple majority, §11.1)" v={r.quorum_met ? 'Met' : 'Not met'} testid="record-quorum" />
          {r.rule && <Row l="Required to pass" v={b.kind === 'amendment' ? 'Two-thirds affirmative vote (§11.4)' : 'Majority vote (§11.3)'} />}
        </tbody></table>
        <p className="text-[12px] uppercase tracking-[0.2em] text-[#241019]/50 mb-2">Tally</p>
        <table className="w-full mb-8" data-testid="record-tally"><tbody>{tally.map(([l, n]) => <Row key={l} l={l} v={n} />)}</tbody></table>
        <p className="text-[16px] mb-12">Result: <b data-testid="record-outcome" className="text-[#3B0A2E]">{outcome}</b></p>
        <p className="text-[12px] text-[#241019]/55 mb-10">Votes were cast by secret ballot through the member portal. One vote per member in good standing (§11.2). No individual choices are recorded.</p>
        <div className="grid grid-cols-2 gap-10 mt-6">
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]"><b data-testid="record-secretary">{b.secretary || '______________________'}</b>, Secretary</p></div>
          <div><div className="border-b border-[#241019] h-10" /><p className="mt-1 text-[12.5px]">Date</p></div>
        </div>
        <p className="text-[10.5px] text-[#241019]/40 mt-12">Record generated {dt(b.generated_at)} · Ref {b.id.slice(0, 8)}</p>
      </article>
    </div>
  );
}
