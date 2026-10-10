import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Pin, Megaphone } from 'lucide-react';
import { fmtDate } from './fmt';
import { HomeCards } from './HomeCards';

export function Announcements({ me }) {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get('/members/announcements').then(({ data }) => setItems(data)).catch(() => setItems([])); }, []);
  if (items === null) return <p className="text-[#241019]/50">Loading…</p>;
  if (!items.length) return (
    <div>
    <HomeCards me={me} />
    <div data-testid="announcements-empty" className="text-center py-14">
      <Megaphone className="mx-auto text-[#B4247E] mb-3" size={30} />
      <p className="text-[#241019]/60">No announcements yet. Check back soon.</p>
    </div>
    </div>
  );
  return (
    <div className="space-y-4" data-testid="announcements-list">
      <HomeCards me={me} />
      {items.map((a) => (
        <article key={a.id} data-testid={`announcement-${a.id}`} className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <div className="flex items-center gap-2 text-[12px] text-[#241019]/50 mb-2">
            {a.pinned && <span className="inline-flex items-center gap-1 text-[#B4247E] font-semibold"><Pin size={12} /> Pinned</span>}
            <span>{a.author_name} · {fmtDate(a.created_at)}</span>
          </div>
          <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-2">{a.title}</h3>
          <p className="text-[14.5px] text-[#241019]/80 whitespace-pre-line leading-relaxed">{a.body}</p>
        </article>
      ))}
    </div>
  );
}
