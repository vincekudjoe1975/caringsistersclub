import React, { useEffect, useState, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Loader2, Search, Check, X, ArrowLeft, UserX } from 'lucide-react';

export default function SessionCheckIn() {
  const { sid } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  const [q, setQ] = useState('');
  const load = useCallback(() => api.get(`/admin/sessions/${sid}/roster`).then(({ data }) => setD(data))
    .catch((e) => setErr([401, 403].includes(e?.response?.status) ? 'auth' : e?.response?.data?.detail || 'Could not load this session.')), [sid]);
  useEffect(() => { load(); }, [load]);
  const mark = async (r, v) => {
    const next = r.attendance === v ? null : v;
    setD((x) => ({ ...x, items: x.items.map((i) => (i.id === r.id ? { ...i, attendance: next } : i)) }));
    await api.post(`/admin/sessions/${sid}/attendance`, { updates: { [r.id]: next } });
  };
  const rest = async () => { if (window.confirm('Mark everyone not checked in as absent?')) { await api.post(`/admin/sessions/${sid}/attendance`, { all: 'no_show' }); load(); } };
  if (err === 'auth') return <div className="min-h-screen flex items-center justify-center p-6 text-center"><p data-testid="sci-auth">Staff sign-in required. <Link to="/login" className="text-[#B4247E] font-semibold">Sign in</Link></p></div>;
  if (err) return <div className="min-h-screen flex items-center justify-center p-6"><p data-testid="sci-error">{err}</p></div>;
  if (!d) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const present = d.items.filter((i) => i.attendance === 'attended').length;
  const list = d.items.filter((i) => !q || `${i.name} ${i.email}`.toLowerCase().includes(q.toLowerCase()));
  return (
    <div className="min-h-screen bg-[#F7EFE9]" data-testid="session-checkin-page">
      <div className="sticky top-0 z-10 px-4 pt-5 pb-4 text-white" style={{ background: '#3B0A2E' }}>
        <Link to="/admin" className="text-[12.5px] text-white/70 flex items-center gap-1 mb-2"><ArrowLeft size={13} /> Admin</Link>
        <h1 data-testid="sci-title" className="font-serif text-[22px] font-semibold leading-tight">{d.program}</h1>
        <p className="text-[12.5px] text-white/70">{d.label}</p>
        <div className="flex items-center gap-3 mt-3">
          <p data-testid="sci-count" className="text-[15px] font-semibold"><span className="text-[#CBA24B]">{present}</span> / {d.items.length} checked in</p>
        </div>
        <div className="relative mt-3"><Search size={16} className="absolute left-3 top-3 text-[#241019]/40" />
          <input data-testid="sci-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or email" className="w-full rounded-xl pl-9 pr-3 py-2.5 text-[15px] text-[#241019]" /></div>
      </div>
      <div className="p-4 space-y-2.5 pb-28">
        {!d.items.length && <p data-testid="sci-empty" className="text-center text-[#241019]/60 py-10">No one has signed up for this session yet.</p>}
        {list.map((r) => (
          <div key={r.id} data-testid={`sci-row-${r.id}`} className={`bg-white rounded-2xl p-4 flex items-center gap-3 transition-colors ${r.attendance === 'attended' ? 'ring-2 ring-green-500/60' : r.attendance === 'no_show' ? 'opacity-60' : ''}`}>
            <div className="flex-1 min-w-0"><p className="font-semibold text-[15.5px] text-[#3B0A2E] truncate">{r.name}</p><p className="text-[12.5px] text-[#241019]/55 truncate">{r.email}{r.phone ? ` · ${r.phone}` : ''}</p></div>
            <button data-testid={`sci-absent-${r.id}`} onClick={() => mark(r, 'no_show')} aria-label="Absent" className={`w-11 h-11 rounded-full flex items-center justify-center transition-colors ${r.attendance === 'no_show' ? 'bg-red-500 text-white' : 'bg-[#F7EFE9] text-[#241019]/50'}`}><X size={20} /></button>
            <button data-testid={`sci-present-${r.id}`} onClick={() => mark(r, 'attended')} aria-label="Present" className={`w-14 h-14 rounded-full flex items-center justify-center transition-colors ${r.attendance === 'attended' ? 'bg-green-600 text-white' : 'bg-[#F7EFE9] text-[#3B0A2E]'}`}><Check size={24} /></button>
          </div>
        ))}
      </div>
      {d.items.length > 0 && (
        <div className="fixed bottom-0 inset-x-0 p-4 bg-white/95 backdrop-blur border-t border-[#3B0A2E]/10">
          <button data-testid="sci-mark-rest" onClick={rest} className="w-full rounded-full py-3.5 font-semibold text-[14px] bg-[#3B0A2E] text-white flex items-center justify-center gap-2"><UserX size={17} /> Finish: mark the rest absent</button>
        </div>
      )}
    </div>
  );
}
