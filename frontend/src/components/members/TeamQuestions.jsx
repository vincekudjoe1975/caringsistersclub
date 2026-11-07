import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { MessagesSquare, Send } from 'lucide-react';

const when = (iso) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

function Thread({ q, mine, onReply }) {
  const [text, setText] = useState('');
  const other = mine ? q.to : q.from;
  const send = async () => { if (await onReply(q, text)) setText(''); };
  return (
    <li data-testid={`team-q-${q.id}`} className="rounded-xl bg-[#F7EFE9] p-4">
      <p className="text-[12px] text-[#241019]/55 mb-1">{mine ? `You asked ${other.name}` : `${other.name} asked you`} · {when(q.created_at)}</p>
      <p className="text-[14px] text-[#241019] whitespace-pre-line">{q.text}</p>
      {(q.replies || []).map((r, i) => (
        <div key={i} className="mt-2.5 pl-3 border-l-2 border-[#B4247E]/40">
          <p className="text-[12px] text-[#241019]/55">{r.by.name} · {when(r.at)}</p>
          <p className="text-[13.5px] text-[#241019] whitespace-pre-line">{r.text}</p>
        </div>
      ))}
      <div className="mt-3 flex gap-2">
        <input data-testid={`team-q-reply-${q.id}`} value={text} onChange={(e) => setText(e.target.value)} placeholder={mine ? 'Add a follow-up…' : 'Write your answer…'}
          className="flex-1 min-w-0 rounded-full border border-[#3B0A2E]/15 bg-white px-4 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]" />
        <button data-testid={`team-q-reply-send-${q.id}`} disabled={!text.trim()} onClick={send} aria-label="Send reply" className="btn-magenta rounded-full w-10 h-10 flex items-center justify-center disabled:opacity-50"><Send size={15} /></button>
      </div>
    </li>
  );
}

export function TeamQuestions() {
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/members/team-questions').then(({ data }) => setD(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!d || (!d.asked.length && !d.received.length)) return null;
  const reply = async (q, text) => {
    try { await api.post(`/members/team-questions/${q.id}/reply`, { text }); toast({ title: 'Reply sent' }); load(); return true; }
    catch (e) { toast({ title: 'Could not send', description: e?.response?.data?.detail, variant: 'destructive' }); return false; }
  };
  return (
    <div data-testid="team-questions" className="mt-8 rounded-2xl bg-white border border-[#3B0A2E]/10 p-5 sm:p-6">
      <p className="flex items-center gap-2 font-serif text-[18px] text-[#3B0A2E] font-semibold mb-4"><MessagesSquare size={17} className="text-[#B4247E]" /> Questions</p>
      <ul className="space-y-3">
        {d.received.map((q) => <Thread key={q.id} q={q} mine={false} onReply={reply} />)}
        {d.asked.map((q) => <Thread key={q.id} q={q} mine onReply={reply} />)}
      </ul>
    </div>
  );
}
