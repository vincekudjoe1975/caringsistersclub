import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { Trash2 } from 'lucide-react';
import { Avatar } from './Avatar';
import { fmtDate } from './fmt';
import { Composer } from './Composer';

const Post = ({ p, canDelete, onDelete, testid }) => (
  <div data-testid={testid} className="flex gap-4 bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
    <Avatar name={p.author_name} src={p.author_picture} />
    <div className="flex-1 min-w-0">
      <p className="text-[12.5px] text-[#241019]/50 mb-1"><span className="font-semibold text-[#3B0A2E]">{p.author_name}</span> · {fmtDate(p.created_at)}</p>
      <p className="text-[14.5px] text-[#241019]/85 whitespace-pre-line leading-relaxed break-words">{p.body}</p>
    </div>
    {canDelete && <button data-testid={`${testid}-delete`} onClick={onDelete} aria-label="Delete" className="text-[#241019]/35 hover:text-red-600 transition-colors self-start"><Trash2 size={16} /></button>}
  </div>
);

export function Thread({ id, me, onDeleted }) {
  const [t, setT] = useState(null);
  const load = useCallback(() => api.get(`/members/threads/${id}`).then(({ data }) => setT(data)), [id]);
  useEffect(() => { load(); }, [load]);
  if (!t) return <p className="text-[#241019]/50">Loading…</p>;
  const mine = (p) => me.is_admin || p.author_id === me.user_id;
  return (
    <div data-testid="thread-view">
      <h2 data-testid="thread-title" className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-4">{t.title}</h2>
      <Post p={t} testid="thread-op" canDelete={mine(t)} onDelete={async () => { if (window.confirm('Delete this conversation?')) { await api.delete(`/members/threads/${id}`); onDeleted(); } }} />
      <div className="ml-6 md:ml-14 mt-3 space-y-3">
        {(t.replies || []).map((r) => (
          <Post key={r.id} p={r} testid={`reply-${r.id}`} canDelete={mine(r)} onDelete={async () => { await api.delete(`/members/threads/${id}/replies/${r.id}`); load(); }} />
        ))}
        <Composer placeholder="Write a reply…" onSubmit={async (p) => { await api.post(`/members/threads/${id}/replies`, p); load(); }} />
      </div>
    </div>
  );
}
