import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Search, ThumbsUp } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';

function Helped({ r, onToggle }) {
  return (
    <button data-testid={`member-faq-helped-${r.id}`} onClick={() => onToggle(r)} aria-pressed={r.helped}
      className={`mt-3 rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold flex items-center gap-1.5 border transition-colors ${r.helped ? 'bg-[#B4247E] text-white border-[#B4247E]' : 'border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E]'}`}>
      <ThumbsUp size={13} /> {r.helped ? 'Thanks! This helped' : 'This helped'}
    </button>
  );
}

export function MemberFaq() {
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState('');
  useEffect(() => { api.get('/members/faq').then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  const toggle = async (r) => {
    setRows((rs) => rs.map((x) => (x.id === r.id ? { ...x, helped: !r.helped } : x)));
    try { await api.post(`/members/faq/${r.id}/helpful`, { helped: !r.helped }); }
    catch { setRows((rs) => rs.map((x) => (x.id === r.id ? { ...x, helped: r.helped } : x))); }
  };
  const words = q.toLowerCase().split(/\s+/).filter(Boolean);
  const list = (rows || []).filter((r) => words.every((w) => `${r.question} ${r.answer}`.toLowerCase().includes(w)));
  return (
    <div data-testid="member-faq">
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-1">Common questions</h2>
      <p className="text-[14px] text-[#241019]/60 mb-5">Answers from the Club team. Can't find yours? Tap "Ask" on a Club team member in the Directory.</p>
      {rows?.length > 0 && (
        <label className="relative block mb-5 max-w-md">
          <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#241019]/40" />
          <input data-testid="member-faq-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search questions, e.g. dues" aria-label="Search the FAQ"
            className="w-full rounded-full border border-[#3B0A2E]/15 bg-white pl-11 pr-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
        </label>
      )}
      {rows === null ? <p className="text-[#241019]/50">Loading…</p> : !rows.length ? (
        <p data-testid="member-faq-empty" className="text-[14px] text-[#241019]/55">No questions here yet. The Club team will add answers soon.</p>
      ) : !list.length ? (
        <p data-testid="member-faq-no-results" className="text-[14px] text-[#241019]/55">Nothing matches "{q}". Try another word, or ask a Club team member in the Directory.</p>
      ) : (
        <Accordion type="single" collapsible className="bg-white rounded-2xl border border-[#3B0A2E]/10 px-5">
          {list.map((r) => (
            <AccordionItem key={r.id} value={r.id} data-testid={`member-faq-item-${r.id}`}>
              <AccordionTrigger className="text-left font-semibold text-[#3B0A2E] text-[15px]">{r.question}</AccordionTrigger>
              <AccordionContent className="text-[14px] text-[#241019]/80">
                <p className="whitespace-pre-line">{r.answer}</p>
                <Helped r={r} onToggle={toggle} />
              </AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      )}
    </div>
  );
}
