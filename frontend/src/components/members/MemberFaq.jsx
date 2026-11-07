import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../ui/accordion';

export function MemberFaq() {
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get('/members/faq').then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  return (
    <div data-testid="member-faq">
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-1">Common questions</h2>
      <p className="text-[14px] text-[#241019]/60 mb-6">Answers from the Club team. Can't find yours? Tap "Ask" on a Club team member in the Directory.</p>
      {rows === null ? <p className="text-[#241019]/50">Loading…</p> : rows.length ? (
        <Accordion type="single" collapsible className="bg-white rounded-2xl border border-[#3B0A2E]/10 px-5">
          {rows.map((r) => (
            <AccordionItem key={r.id} value={r.id} data-testid={`member-faq-item-${r.id}`}>
              <AccordionTrigger className="text-left font-semibold text-[#3B0A2E] text-[15px]">{r.question}</AccordionTrigger>
              <AccordionContent className="text-[14px] text-[#241019]/80 whitespace-pre-line">{r.answer}</AccordionContent>
            </AccordionItem>
          ))}
        </Accordion>
      ) : <p data-testid="member-faq-empty" className="text-[14px] text-[#241019]/55">No questions here yet. The Club team will add answers soon.</p>}
    </div>
  );
}
