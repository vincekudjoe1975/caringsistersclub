import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { QRCodeSVG } from 'qrcode.react';
import { HandHeart, Sparkles, Trash2, CheckCircle2, Send, Star, X } from 'lucide-react';
import { Avatar } from './Avatar';
import { fmtDate } from './fmt';

export function CheckinCode() {
  const [code, setCode] = useState('');
  useEffect(() => { api.get('/members/checkin-code').then(({ data }) => setCode(data.code)).catch(() => {}); }, []);
  if (!code) return null;
  return (
    <div data-testid="checkin-code-card" className="max-w-xl mt-8 bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 flex items-center gap-5">
      <div data-testid="checkin-qr" className="bg-white p-2 rounded-xl border border-[#3B0A2E]/10"><QRCodeSVG value={code} size={112} fgColor="#3B0A2E" /></div>
      <div><p className="font-semibold text-[#3B0A2E]">My check-in code</p><p className="text-[13px] text-[#241019]/65 mt-1">Show this at the door of meetings and gatherings so staff can check you in with one scan.</p></div>
    </div>
  );
}

const src = (u) => (u && u.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u);
const monthLabel = (m) => new Date(m + '-15').toLocaleDateString(undefined, { month: 'long', year: 'numeric' });

export function SpotlightArchive() {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState(null);
  useEffect(() => { api.get('/members/spotlights').then(({ data }) => setRows(data)).catch(() => setRows([])); }, []);
  if (rows === null) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div>
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-5">Sisterhood Spotlights</h2>
      {!rows.length && <p data-testid="spotlights-empty" className="text-[#241019]/60">No spotlights yet.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="spotlight-gallery">
        {rows.map((s) => (
          <button key={s.id} data-testid={`spotlight-tile-${s.id}`} onClick={() => setOpen(s)} className="text-left bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 hover:-translate-y-1 transition-transform duration-300">
            {s.photo_url ? <img src={src(s.photo_url)} alt={s.name} referrerPolicy="no-referrer" className="w-full h-52 object-cover" /> : <div className="h-52" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }} />}
            <div className="p-4"><p className="text-[11.5px] text-[#CBA24B] font-semibold uppercase tracking-wider">{monthLabel(s.month)}</p><p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">{s.name}</p><p className="text-[13px] text-[#241019]/65 line-clamp-2 mt-1">{s.story}</p></div>
          </button>
        ))}
      </div>
      {open && (
        <div data-testid="spotlight-modal" className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4" onClick={() => setOpen(null)}>
          <div className="bg-white rounded-3xl max-w-2xl w-full max-h-[90vh] overflow-auto" onClick={(e) => e.stopPropagation()}>
            {open.photo_url && <img src={src(open.photo_url)} alt={open.name} referrerPolicy="no-referrer" className="w-full max-h-96 object-cover" />}
            <div className="p-7">
              <div className="flex justify-between"><p className="eyebrow text-[#CBA24B] flex items-center gap-2"><Star size={14} /> {monthLabel(open.month)}</p><button data-testid="spotlight-modal-close" onClick={() => setOpen(null)}><X size={20} /></button></div>
              <h3 className="font-serif text-[28px] text-[#3B0A2E] font-semibold mt-1 mb-3">{open.name}</h3>
              <p className="text-[15px] text-[#241019]/80 leading-relaxed whitespace-pre-line">{open.story}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function PrayerCard({ p, me, reload }) {
  const [text, setText] = useState('');
  const pray = async () => { await api.post(`/members/prayers/${p.id}/pray`); reload(); };
  const encourage = async (e) => { e.preventDefault(); if (!text.trim()) return; await api.post(`/members/prayers/${p.id}/encourage`, { body: text }); setText(''); reload(); };
  return (
    <article data-testid={`prayer-${p.id}`} className={`bg-white rounded-2xl p-5 border ${p.kind === 'praise' ? 'border-[#CBA24B]/50' : 'border-[#3B0A2E]/8'}`}>
      <div className="flex items-center gap-3 mb-2">
        <Avatar name={p.author_name} src={p.author_picture} size={36} />
        <div className="flex-1 min-w-0"><p className="text-[13.5px] font-semibold text-[#3B0A2E]">{p.author_name}{p.anonymous && (p.mine || me.is_admin) ? <span className="text-[11px] text-[#241019]/45 font-normal"> (posted anonymously)</span> : ''}</p>
          <p className="text-[11.5px] text-[#241019]/50">{p.kind === 'praise' ? 'Praise report' : 'Prayer request'} · {fmtDate(p.created_at)}</p></div>
        {p.answered_at && <span data-testid={`prayer-answered-${p.id}`} className="text-[11.5px] font-semibold text-green-700 bg-green-50 rounded-full px-2.5 py-0.5 flex items-center gap-1"><CheckCircle2 size={12} /> Answered</span>}
        {(p.mine || me.is_admin) && <button data-testid={`prayer-del-${p.id}`} onClick={async () => { if (window.confirm('Remove this post?')) { await api.delete(`/members/prayers/${p.id}`); reload(); } }} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={15} /></button>}
      </div>
      <p className="text-[14.5px] text-[#241019]/85 whitespace-pre-line leading-relaxed">{p.body}</p>
      <div className="flex flex-wrap items-center gap-3 mt-3">
        <button data-testid={`prayer-pray-${p.id}`} onClick={pray} className={`rounded-full px-4 py-1.5 text-[13px] font-semibold flex items-center gap-1.5 transition-colors ${p.i_am_praying ? 'bg-[#3B0A2E] text-white' : 'border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E]'}`}>
          <HandHeart size={14} /> {p.kind === 'praise' ? 'Rejoicing' : 'Praying'} · <span data-testid={`prayer-count-${p.id}`}>{p.praying_count}</span>
        </button>
        {p.mine && p.kind === 'request' && <button data-testid={`prayer-mark-${p.id}`} onClick={async () => { await api.post(`/members/prayers/${p.id}/answered`); reload(); }} className="text-[12.5px] font-semibold text-[#B4247E]">{p.answered_at ? 'Mark not answered' : 'Mark as answered'}</button>}
      </div>
      {p.encouragements.length > 0 && (
        <div className="mt-3 space-y-2 pl-4 border-l-2 border-[#F7EFE9]">
          {p.encouragements.map((e) => (
            <div key={e.id} className="text-[13.5px] flex gap-2"><span className="flex-1"><b className="text-[#3B0A2E]">{e.author_name}:</b> <span className="text-[#241019]/80">{e.body}</span></span>
              {(e.mine || me.is_admin) && <button data-testid={`enc-del-${e.id}`} onClick={async () => { await api.delete(`/members/prayers/${p.id}/encourage/${e.id}`); reload(); }} className="text-[#241019]/30 hover:text-red-600"><Trash2 size={12} /></button>}</div>
          ))}
        </div>
      )}
      <form onSubmit={encourage} className="flex gap-2 mt-3">
        <input data-testid={`enc-input-${p.id}`} value={text} onChange={(e) => setText(e.target.value)} placeholder="Leave a word of encouragement…" className="flex-1 rounded-full border border-[#3B0A2E]/15 px-4 py-2 text-[13px] focus:outline-none focus:border-[#B4247E]" />
        <button data-testid={`enc-send-${p.id}`} className="text-[#B4247E] px-2"><Send size={16} /></button>
      </form>
    </article>
  );
}

export function PrayerBoard({ me }) {
  const [rows, setRows] = useState(null);
  const [f, setF] = useState({ kind: 'request', body: '', anonymous: false });
  const [err, setErr] = useState('');
  const load = useCallback(() => api.get('/members/prayers').then(({ data }) => setRows(data)).catch(() => setRows([])), []);
  useEffect(() => { load(); }, [load]);
  const post = async (e) => {
    e.preventDefault(); setErr('');
    try { await api.post('/members/prayers', f); setF({ ...f, body: '', anonymous: false }); load(); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not post.'); }
  };
  return (
    <div className="max-w-3xl">
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2"><Sparkles size={20} className="text-[#CBA24B]" /> Prayer & Support</h2>
      <p className="text-[13.5px] text-[#241019]/60 mb-5">A private space for our sisters only. Share what's on your heart, or celebrate what God has done.</p>
      <form onSubmit={post} data-testid="prayer-form" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-6 space-y-3">
        <div className="flex gap-1">{[['request', 'Prayer request'], ['praise', 'Praise report']].map(([k, l]) => <button type="button" key={k} data-testid={`prayer-kind-${k}`} onClick={() => setF({ ...f, kind: k })} className={`rounded-full px-4 py-1.5 text-[13px] font-semibold ${f.kind === k ? 'bg-[#3B0A2E] text-white' : 'bg-[#F7EFE9] text-[#3B0A2E]'}`}>{l}</button>)}</div>
        <textarea data-testid="prayer-body" rows={3} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} placeholder={f.kind === 'praise' ? 'Share your good news…' : 'How can your sisters pray for you?'} className="w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-[13px] text-[#241019]/75"><input data-testid="prayer-anon" type="checkbox" checked={f.anonymous} onChange={(e) => setF({ ...f, anonymous: e.target.checked })} className="accent-[#B4247E]" /> Post anonymously (staff can still see it's you)</label>
          <button data-testid="prayer-post-btn" disabled={!f.body.trim()} className="btn-magenta rounded-full px-5 py-2 text-[13.5px] font-semibold ml-auto disabled:opacity-50">Share</button>
        </div>
        {err && <p className="text-red-600 text-[13px]">{err}</p>}
      </form>
      {rows === null ? <p className="text-[#241019]/50">Loading…</p> : !rows.length ? <p data-testid="prayers-empty" className="text-center text-[#241019]/60 py-10">No posts yet. Be the first to share.</p>
        : <div className="space-y-4" data-testid="prayer-list">{rows.map((p) => <PrayerCard key={p.id} p={p} me={me} reload={load} />)}</div>}
    </div>
  );
}
