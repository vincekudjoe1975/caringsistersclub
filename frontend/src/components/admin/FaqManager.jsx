import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Switch } from '../ui/switch';
import { Plus, Pencil, Trash2, Save, X, ThumbsUp } from 'lucide-react';
import { OpenQuestions } from './OpenQuestions';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const blank = { question: '', answer: '', published: true };

function Editor({ f, setF, onSave, onCancel }) {
  return (
    <div data-testid="faq-editor" className="p-5 space-y-3 bg-[#F7EFE9]/60">
      {f.source_question_id && <p className="text-[12px] text-[#241019]/60">Taken from a sister's question. Edit it so it reads well for everyone; her name is never shown.</p>}
      <input data-testid="faq-question-input" value={f.question} onChange={(e) => setF({ ...f, question: e.target.value })} maxLength={300} placeholder="Question" className={inputCls} />
      <textarea data-testid="faq-answer-input" rows={4} value={f.answer} onChange={(e) => setF({ ...f, answer: e.target.value })} maxLength={3000} placeholder="Answer" className={inputCls} />
      <div className="flex flex-wrap items-center justify-between gap-3">
        <label className="flex items-center gap-2 text-[13px] font-semibold text-[#3B0A2E]"><Switch data-testid="faq-published-toggle" checked={f.published} onCheckedChange={(v) => setF({ ...f, published: v })} /> Show to members</label>
        <div className="flex gap-2">
          <button data-testid="faq-cancel-btn" onClick={onCancel} className="rounded-full px-4 py-2 text-[13px] font-semibold text-[#241019]/60 flex items-center gap-1"><X size={14} /> Cancel</button>
          <button data-testid="faq-save-btn" onClick={onSave} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Save size={14} /> Save</button>
        </div>
      </div>
    </div>
  );
}

export function FaqManager({ toast, draft, clearDraft }) {
  const [rows, setRows] = useState([]);
  const [edit, setEdit] = useState(null);
  const load = useCallback(() => api.get('/admin/faq').then(({ data }) => setRows(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => { if (draft) { setEdit({ ...blank, ...draft }); clearDraft(); document.querySelector('[data-testid=faq-manager]')?.scrollIntoView({ behavior: 'smooth' }); } }, [draft, clearDraft]);
  const save = async () => {
    try {
      if (edit.id) await api.put(`/admin/faq/${edit.id}`, edit); else await api.post('/admin/faq', edit);
      toast({ title: 'FAQ saved', description: edit.published ? 'Members can see it under FAQ in the portal.' : 'Saved as hidden.' }); setEdit(null); load();
    } catch (e) { toast({ title: 'Could not save', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };
  const del = async (r) => { if (!window.confirm(`Delete "${r.question}"?`)) return; await api.delete(`/admin/faq/${r.id}`); load(); };
  return (
    <div data-testid="faq-manager" className="bg-white rounded-2xl border border-[#3B0A2E]/8">
      <div className="p-5 flex items-center justify-between gap-3 border-b border-[#3B0A2E]/8">
        <div><p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Member FAQ</p><p className="text-[12.5px] text-[#241019]/60">Shown on the FAQ tab of the member portal.</p></div>
        <button data-testid="faq-add-btn" onClick={() => setEdit({ ...blank })} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Plus size={14} /> New entry</button>
      </div>
      {edit && <Editor f={edit} setF={setEdit} onSave={save} onCancel={() => setEdit(null)} />}
      <ul className="divide-y divide-[#3B0A2E]/8">
        {rows.length ? rows.map((r) => (
          <li key={r.id} data-testid={`faq-row-${r.id}`} className="p-4 flex items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="text-[14px] font-semibold text-[#3B0A2E]">{r.question} {!r.published && <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#f0ece4] text-[#8a6d2f] ml-1">Hidden</span>}{r.starter && <span data-testid={`faq-starter-${r.id}`} className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#FFF4DD] text-[#8a6d2f] ml-1">Starter entry · check the wording</span>}</p>
              <p className="text-[13px] text-[#241019]/65 line-clamp-2">{r.answer}</p>
              <p data-testid={`faq-helpful-${r.id}`} className="text-[12px] text-[#B4247E] font-semibold mt-1 flex items-center gap-1"><ThumbsUp size={12} /> {r.helpful_count || 0} sister{r.helpful_count === 1 ? '' : 's'} found this helpful</p>
            </div>
            <div className="flex gap-1 shrink-0">
              <button data-testid={`faq-edit-${r.id}`} aria-label="Edit" onClick={() => setEdit(r)} className="p-2 text-[#241019]/50 hover:text-[#B4247E]"><Pencil size={15} /></button>
              <button data-testid={`faq-delete-${r.id}`} aria-label="Delete" onClick={() => del(r)} className="p-2 text-[#241019]/50 hover:text-red-600"><Trash2 size={15} /></button>
            </div>
          </li>
        )) : <li data-testid="faq-empty" className="p-5 text-[13px] text-[#241019]/55">No FAQ entries yet. Add one, or use "Add to FAQ" on an answered question.</li>}
      </ul>
    </div>
  );
}

export function AdminQuestions({ toast }) {
  const [draft, setDraft] = useState(null);
  const clear = useCallback(() => setDraft(null), []);
  return (
    <div data-testid="admin-questions" className="space-y-6">
      <OpenQuestions toast={toast} onFaq={setDraft} />
      <FaqManager toast={toast} draft={draft} clearDraft={clear} />
    </div>
  );
}
