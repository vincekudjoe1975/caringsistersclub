import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { MessageCircle, Plus, ArrowLeft } from 'lucide-react';
import { Avatar } from './Avatar';
import { fmtDate } from './fmt';
import { Thread } from './Thread';
import { Composer } from './Composer';

export function Discussion({ me }) {
  const [threads, setThreads] = useState(null);
  const [open, setOpen] = useState(null);
  const [writing, setWriting] = useState(false);
  const load = useCallback(() => api.get('/members/threads').then(({ data }) => setThreads(data)).catch(() => setThreads([])), []);
  useEffect(() => { load(); }, [load]);

  if (open) return (
    <div>
      <button data-testid="thread-back-btn" onClick={() => { setOpen(null); load(); }} className="text-[#B4247E] text-[14px] font-semibold flex items-center gap-1.5 mb-5"><ArrowLeft size={15} /> All conversations</button>
      <Thread id={open} me={me} onDeleted={() => { setOpen(null); load(); }} />
    </div>
  );

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Sister conversations</h2>
        {!writing && <button data-testid="new-thread-btn" onClick={() => setWriting(true)} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-1.5"><Plus size={15} /> Start a conversation</button>}
      </div>
      {writing && <Composer withTitle onCancel={() => setWriting(false)} onSubmit={async (p) => { const { data } = await api.post('/members/threads', p); setWriting(false); setOpen(data.id); }} />}
      {threads === null ? <p className="text-[#241019]/50">Loading…</p> : !threads.length ? (
        <p data-testid="threads-empty" className="text-center text-[#241019]/60 py-12">No conversations yet. Be the first to say hello!</p>
      ) : (
        <div className="space-y-3" data-testid="threads-list">
          {threads.map((t) => (
            <button key={t.id} data-testid={`thread-item-${t.id}`} onClick={() => setOpen(t.id)} className="w-full text-left bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 flex gap-4 hover:border-[#B4247E]/40 hover:-translate-y-0.5 transition-[transform,border-color] duration-200">
              <Avatar name={t.author_name} src={t.author_picture} />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-[#3B0A2E] text-[15.5px] truncate">{t.title}</p>
                <p className="text-[13.5px] text-[#241019]/65 line-clamp-1">{t.body}</p>
                <p className="text-[12px] text-[#241019]/45 mt-1">{t.author_name} · {fmtDate(t.created_at)}</p>
              </div>
              <span className="text-[13px] text-[#B4247E] flex items-center gap-1 shrink-0"><MessageCircle size={14} /> {t.reply_count || 0}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
