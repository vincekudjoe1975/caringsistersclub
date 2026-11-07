import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Switch } from '../ui/switch';
import { CheckCircle2, Circle, BookOpen } from 'lucide-react';

const when = (iso) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

function QRow({ q, onMark, onFaq }) {
  const last = [...(q.replies || [])].reverse().find((r) => r.by.user_id === q.to.user_id);
  return (
    <li data-testid={`admin-q-${q.id}`} className={`p-4 ${q.answered_at ? 'opacity-70' : ''}`}>
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-[12px] text-[#241019]/55">{q.from.name} asked {q.to.name} · {when(q.created_at)} · {(q.replies || []).length} repl{(q.replies || []).length === 1 ? 'y' : 'ies'}</p>
          <p className="text-[14px] text-[#241019] mt-0.5 line-clamp-3 whitespace-pre-line">{q.text}</p>
          {last && <p className="text-[12.5px] text-[#241019]/65 mt-1 pl-3 border-l-2 border-[#B4247E]/40 line-clamp-2">{last.text}</p>}
        </div>
        <div className="flex flex-wrap gap-2 shrink-0">
          <button data-testid={`admin-q-mark-${q.id}`} onClick={() => onMark(q, !q.answered_at)} className={`rounded-full px-3 py-1.5 text-[12px] font-semibold flex items-center gap-1 border transition-colors ${q.answered_at ? 'border-[#1f7a4d]/30 text-[#1f7a4d]' : 'border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#1f7a4d] hover:text-[#1f7a4d]'}`}>
            {q.answered_at ? <><CheckCircle2 size={13} /> Answered</> : <><Circle size={13} /> Mark answered</>}
          </button>
          <button data-testid={`admin-q-faq-${q.id}`} onClick={() => onFaq({ question: q.text, answer: last?.text || '', source_question_id: q.id })} className="rounded-full px-3 py-1.5 text-[12px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] flex items-center gap-1 transition-colors"><BookOpen size={13} /> Add to FAQ</button>
        </div>
      </div>
    </li>
  );
}

export function OpenQuestions({ toast, onFaq }) {
  const [rows, setRows] = useState(null);
  const [cfg, setCfg] = useState(null);
  const [show, setShow] = useState('open');
  const load = useCallback(() => api.get('/admin/team-questions').then(({ data }) => setRows(data)).catch(() => setRows([])), []);
  useEffect(() => { load(); api.get('/admin/team-questions/settings').then(({ data }) => setCfg(data)).catch(() => {}); }, [load]);
  const mark = async (q, answered) => {
    try { await api.post(`/admin/team-questions/${q.id}/answered`, { answered }); load(); }
    catch (e) { toast({ title: 'Could not update', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };
  const share = async (all_staff) => {
    try { await api.put('/admin/team-questions/settings', { all_staff }); setCfg({ ...cfg, all_staff }); load(); }
    catch (e) { toast({ title: 'Could not update', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };
  if (!rows) return null;
  const open = rows.filter((q) => !q.answered_at);
  const list = show === 'open' ? open : rows.filter((q) => q.answered_at);
  return (
    <div data-testid="open-questions" className="bg-white rounded-2xl border border-[#3B0A2E]/8">
      <div className="p-5 flex flex-wrap items-center justify-between gap-3 border-b border-[#3B0A2E]/8">
        <div>
          <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Sisters' questions <span data-testid="open-questions-count" className="ml-1 text-[12px] font-sans font-semibold px-2 py-0.5 rounded-full bg-[#B4247E] text-white">{open.length} open</span></p>
          <p className="text-[12.5px] text-[#241019]/60">{cfg?.all_staff ? 'Every staff member can see all questions.' : cfg?.can_edit ? 'You see all questions; other staff see only questions sent to them.' : 'Questions sent to you.'} Reply in the member portal or by email.</p>
        </div>
        <div className="flex gap-1">{['open', 'answered'].map((k) => <button key={k} data-testid={`open-questions-filter-${k}`} onClick={() => setShow(k)} className={`rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold ${show === k ? 'bg-[#3B0A2E] text-white' : 'text-[#3B0A2E] border border-[#3B0A2E]/15'}`}>{k === 'open' ? 'Open' : 'Answered'}</button>)}</div>
      </div>
      {cfg?.can_edit && (
        <label className="px-5 py-3 flex items-center justify-between gap-3 text-[13px] font-semibold text-[#3B0A2E] border-b border-[#3B0A2E]/8">
          Let all staff see every question <Switch data-testid="open-questions-share-toggle" checked={cfg.all_staff} onCheckedChange={share} aria-label="Let all staff see every question" />
        </label>
      )}
      <ul className="divide-y divide-[#3B0A2E]/8">
        {list.length ? list.map((q) => <QRow key={q.id} q={q} onMark={mark} onFaq={onFaq} />) : <li data-testid="open-questions-empty" className="p-5 text-[13px] text-[#241019]/55">{show === 'open' ? 'No open questions. Lovely!' : 'Nothing marked answered yet.'}</li>}
      </ul>
    </div>
  );
}
