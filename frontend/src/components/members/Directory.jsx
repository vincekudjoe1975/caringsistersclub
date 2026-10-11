import React, { Suspense, lazy, useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Search, MapPin, Mail, Phone, List, Map as MapIcon } from 'lucide-react';

const SisterMap = lazy(() => import('./SisterMap'));
import { Avatar } from './Avatar';
import { fmtDate } from './fmt';

export function Directory() {
  const [rows, setRows] = useState(null);
  const [q, setQ] = useState('');
  const [view, setView] = useState('list');
  useEffect(() => { api.get('/members/directory').then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  const list = (rows || []).filter((m) => `${m.name} ${m.city}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-4 mb-6">
        <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Our sisters <span className="text-[#241019]/40 text-[16px]">({rows?.length || 0})</span></h2>
        <div className="flex flex-wrap items-center gap-2">
        <div className="flex rounded-full bg-white border border-[#3B0A2E]/15 p-1" role="tablist">
          {[['list', 'List', List], ['map', 'Map', MapIcon]].map(([k, l, I]) => (
            <button key={k} data-testid={`directory-view-${k}`} onClick={() => setView(k)} className={`rounded-full px-4 py-1.5 text-[13px] font-semibold flex items-center gap-1.5 transition-colors ${view === k ? 'bg-[#3B0A2E] text-white' : 'text-[#3B0A2E]'}`}><I size={13} /> {l}</button>
          ))}
        </div>
        {view === 'list' && <label className="relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#241019]/40" />
          <input data-testid="directory-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search by name or city" className="rounded-full border border-[#3B0A2E]/15 pl-9 pr-4 py-2 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] w-full sm:w-64" />
        </label>}
        </div>
      </div>
      {view === 'map' ? <Suspense fallback={<p className="text-[#241019]/50">Loading map…</p>}><SisterMap /></Suspense> : rows === null ? <p className="text-[#241019]/50">Loading…</p> : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4" data-testid="directory-list">
          {list.map((m) => (
            <div key={m.user_id} data-testid={`directory-card-${m.user_id}`} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 hover:-translate-y-0.5 transition-transform duration-200">
              <div className="flex items-center gap-3 mb-3">
                <Avatar name={m.name} src={m.picture} size={48} />
                <div className="min-w-0">
                  <p className="font-semibold text-[#3B0A2E] truncate">{m.name}</p>
                  {m.office && <p className="text-[12px] text-[#B4247E] font-semibold">{m.office}</p>}
                  {m.member_since && <p className="text-[12px] text-[#241019]/45">Member since {fmtDate(m.member_since)}</p>}
                </div>
              </div>
              {m.city && <p className="text-[13px] text-[#241019]/70 flex items-center gap-1.5"><MapPin size={13} className="text-[#B4247E]" /> {m.city}</p>}
              {m.bio && <p className="text-[13.5px] text-[#241019]/75 mt-2 line-clamp-3">{m.bio}</p>}
              {(m.email || m.phone) && (
                <div className="mt-3 pt-3 border-t border-[#3B0A2E]/8 space-y-1 text-[13px]">
                  {m.email && <a href={`mailto:${m.email}`} className="flex items-center gap-1.5 text-[#B4247E] truncate"><Mail size={13} /> {m.email}</a>}
                  {m.phone && <a href={`tel:${m.phone}`} className="flex items-center gap-1.5 text-[#B4247E]"><Phone size={13} /> {m.phone}</a>}
                </div>
              )}
            </div>
          ))}
          {!list.length && <p data-testid="directory-empty" className="text-[#241019]/60 col-span-full text-center py-10">No members match your search.</p>}
        </div>
      )}
    </div>
  );
}
