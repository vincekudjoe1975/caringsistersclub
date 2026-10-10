import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { Vote, Lock, CheckCircle2, Loader2 } from 'lucide-react';

const KIND = { resolution: 'Resolution', amendment: 'Bylaw amendment', election: 'Election' };
const dt = (iso) => new Date(iso).toLocaleString(undefined, { month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit' });

export function Results({ b }) {
  const r = b.results;
  if (!r) return null;
  const rows = b.kind === 'election'
    ? [...b.candidates.map((c) => [c.name, r.counts[c.user_id] || 0]), ['Abstain', r.counts.abstain || 0]]
    : [['Yes', r.yes], ['No', r.no], ['Abstain', r.abstain]];
  const max = Math.max(1, ...rows.map((x) => x[1]));
  return (
    <div data-testid={`results-${b.id}`} className="mt-4 space-y-2">
      {rows.map(([l, n]) => (
        <div key={l} className="text-[13px]">
          <div className="flex justify-between mb-1"><span className="text-[#241019]/80">{l}</span><b className="text-[#3B0A2E]">{n}</b></div>
          <div className="h-2 rounded-full bg-[#F7EFE9] overflow-hidden"><div className="h-full rounded-full bg-[#B4247E] transition-[width] duration-700" style={{ width: `${(n / max) * 100}%` }} /></div>
        </div>
      ))}
      <p className="text-[12.5px] text-[#241019]/60 pt-1">{r.voters} of {r.eligible} eligible members voted · quorum {r.quorum_met ? 'met' : 'not met'}{r.rule ? ` · ${r.rule}` : ''}</p>
      {b.state === 'closed' && <p data-testid={`outcome-${b.id}`} className="font-semibold text-[14px] text-[#3B0A2E]">
        {b.kind === 'election' ? (r.winner ? `Elected: ${r.winner}` : r.tie ? 'Tie: the Elections Committee will decide next steps' : 'No winner (quorum not met or no votes)') : r.passed ? 'Passed' : 'Did not pass'}
      </p>}
    </div>
  );
}

function BallotCard({ b, onVoted }) {
  const [choice, setChoice] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const opts = b.kind === 'election' ? [...b.candidates.map((c) => [c.user_id, c.name]), ['abstain', 'Abstain']] : [['yes', 'Yes'], ['no', 'No'], ['abstain', 'Abstain']];
  const vote = async () => {
    setBusy(true); setErr('');
    try { await api.post(`/members/ballots/${b.id}/vote`, { choice }); onVoted(); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not record your vote.'); setBusy(false); }
  };
  return (
    <article data-testid={`ballot-${b.id}`} className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
      <div className="flex flex-wrap items-center gap-2 text-[12px] mb-2">
        <span className="px-2.5 py-0.5 rounded-full bg-[#faf2f7] text-[#B4247E] font-semibold">{KIND[b.kind]}{b.position ? `: ${b.position}` : ''}</span>
        <span className={`px-2.5 py-0.5 rounded-full font-semibold ${b.state === 'open' ? 'bg-green-100 text-green-800' : 'bg-[#F7EFE9] text-[#241019]/60'}`}>{b.state === 'open' ? 'Voting open' : b.state === 'scheduled' ? 'Opens soon' : 'Closed'}</span>
      </div>
      <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold">{b.title}</h3>
      {b.description && <p className="text-[14px] text-[#241019]/75 whitespace-pre-line mt-2">{b.description}</p>}
      <p className="text-[12.5px] text-[#241019]/50 mt-2">{b.state === 'scheduled' ? `Opens ${dt(b.opens_at)}` : `Closes ${dt(b.closes_at)}`}</p>
      {b.state === 'open' && (b.has_voted ? (
        <p data-testid={`voted-${b.id}`} className="mt-4 text-green-700 font-semibold text-[14px] flex items-center gap-2"><CheckCircle2 size={16} /> Your secret vote has been recorded.</p>
      ) : b.can_vote ? (
        <div className="mt-4">
          <div className="flex flex-wrap gap-2">
            {opts.map(([v, l]) => (
              <button key={v} data-testid={`choice-${b.id}-${v}`} onClick={() => setChoice(v)} className={`rounded-full px-5 py-2 text-[14px] font-semibold border transition-colors ${choice === v ? 'bg-[#3B0A2E] text-white border-[#3B0A2E]' : 'border-[#3B0A2E]/20 text-[#3B0A2E] hover:border-[#B4247E]'}`}>{l}</button>
            ))}
          </div>
          <button data-testid={`cast-${b.id}`} disabled={!choice || busy} onClick={vote} className="btn-magenta rounded-full px-6 py-2.5 text-[14px] font-semibold mt-4 flex items-center gap-2 disabled:opacity-50">{busy ? <Loader2 className="animate-spin" size={15} /> : <Lock size={15} />} Cast secret vote</button>
          <p className="text-[12px] text-[#241019]/50 mt-2">Votes are anonymous. Staff see totals only, and you can't change your vote once it's cast.</p>
          {err && <p data-testid={`vote-error-${b.id}`} className="text-red-600 text-[13px] mt-2">{err}</p>}
        </div>
      ) : (
        <p data-testid={`cannot-vote-${b.id}`} className="mt-4 text-[13.5px] text-red-600">Only members in good standing can vote. See My Dues for details.</p>
      ))}
      {b.state === 'closed' && <Results b={b} />}
    </article>
  );
}

export function Ballots() {
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/members/ballots').then(({ data }) => setD(data)), []);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div>
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-1">Votes & elections</h2>
      <p className="text-[13.5px] text-[#241019]/60 mb-6">Each member in good standing has one vote (Article XI). Bylaw amendments need a two-thirds majority.</p>
      {!d.ballots.length ? (
        <div data-testid="ballots-empty" className="text-center py-12"><Vote className="mx-auto text-[#B4247E] mb-3" size={30} /><p className="text-[#241019]/60">No votes right now.</p></div>
      ) : <div className="space-y-4" data-testid="ballots-list">{d.ballots.map((b) => <BallotCard key={b.id} b={b} onVoted={load} />)}</div>}
    </div>
  );
}
