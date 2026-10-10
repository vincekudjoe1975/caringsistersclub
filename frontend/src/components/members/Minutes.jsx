import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';
import { FileText, ChevronDown, Printer } from 'lucide-react';
import { fmtDate } from './fmt';

export function Minutes() {
  const [rows, setRows] = useState(null);
  const [votes, setVotes] = useState([]);
  const [reports, setReports] = useState([]);
  const [open, setOpen] = useState(null);
  useEffect(() => {
    api.get('/members/minutes').then(({ data }) => setRows(data)).catch(() => setRows([]));
    api.get('/members/treasurer-reports').then(({ data }) => setReports(data)).catch(() => {});
    api.get('/members/ballots').then(({ data }) => setVotes(data.ballots.filter((b) => b.state === 'closed'))).catch(() => {});
  }, []);
  if (rows === null) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div className="grid lg:grid-cols-[1.5fr_1fr] gap-6">
      <div data-testid="minutes-list">
        <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-4">Meeting minutes</h2>
        {!rows.length && <p data-testid="minutes-empty" className="text-[#241019]/60">No approved minutes yet.</p>}
        <div className="space-y-3">
          {rows.map((m) => (
            <div key={m.id} data-testid={`minutes-${m.id}`} className="bg-white rounded-2xl border border-[#3B0A2E]/8">
              <button data-testid={`minutes-toggle-${m.id}`} onClick={() => setOpen(open === m.id ? null : m.id)} className="w-full p-5 flex items-center justify-between text-left">
                <span className="flex items-center gap-3"><FileText size={18} className="text-[#B4247E]" /><span><b className="text-[#3B0A2E]">{m.title}</b><span className="block text-[12px] text-[#241019]/50">{fmtDate(m.date + 'T12:00:00')} · approved {fmtDate(m.minutes.approved_at)}</span></span></span>
                <ChevronDown size={18} className={`transition-transform ${open === m.id ? 'rotate-180' : ''}`} />
              </button>
              {open === m.id && <p className="px-5 pb-5 text-[14.5px] text-[#241019]/80 whitespace-pre-line leading-relaxed">{m.minutes.body}</p>}
            </div>
          ))}
        </div>
      </div>
      <div className="space-y-5 self-start">
      {reports.length > 0 && (
        <div data-testid="treasurer-reports" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
          <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-3">Treasurer's reports</h3>
          {reports.map((r) => (
            <Link key={r.id} to={`/treasurer-report/${r.id}`} target="_blank" data-testid={`treasurer-link-${r.id}`} className="flex items-center justify-between py-2 text-[13.5px] border-b border-[#3B0A2E]/8 last:border-0 hover:text-[#B4247E] transition-colors">
              <span>{r.label}</span><Printer size={14} />
            </Link>
          ))}
        </div>
      )}
      <div data-testid="vote-records" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
        <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-1">Official vote records</h3>
        <p className="text-[12.5px] text-[#241019]/55 mb-3">Recorded by the Secretary under Section 11.5.</p>
        {!votes.length ? <p className="text-[13px] text-[#241019]/50">No closed votes yet.</p> : votes.map((b) => (
          <Link key={b.id} to={`/vote-record/${b.id}`} target="_blank" data-testid={`record-link-${b.id}`} className="flex items-center justify-between py-2 text-[13.5px] border-b border-[#3B0A2E]/8 last:border-0 hover:text-[#B4247E] transition-colors">
            <span className="truncate">{b.title}</span><Printer size={14} className="shrink-0" />
          </Link>
        ))}
      </div>
      </div>
    </div>
  );
}
