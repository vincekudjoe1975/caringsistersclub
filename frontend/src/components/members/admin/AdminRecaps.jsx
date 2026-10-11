import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { Eye, Send, Check, Loader2 } from 'lucide-react';

const src = (u) => `${process.env.REACT_APP_BACKEND_URL}${u}`;

function RecapEditor({ g, reload }) {
  const [sel, setSel] = useState(g.photos.slice(0, 6).map((p) => p.id));
  const [note, setNote] = useState('');
  const [html, setHtml] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const toggle = (id) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : s.length >= 6 ? s : [...s, id]));
  const preview = async () => { const { data } = await api.post(`/admin/members/recaps/${g.id}/preview`, { photo_ids: sel, note }); setHtml(data.html); };
  const send = async () => {
    if (!window.confirm('Email this recap to all active members?')) return;
    setBusy(true);
    try { await api.post(`/admin/members/recaps/${g.id}/send`, { photo_ids: sel, note }); setMsg('Recap is on its way to all active members.'); reload(); }
    catch (ex) { setMsg(ex?.response?.data?.detail || 'Could not send'); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid={`recap-editor-${g.id}`} className="mt-4">
      <p className="text-[12.5px] text-[#241019]/60 mb-2">Pick up to 6 photos ({sel.length}/6 selected)</p>
      <div className="grid grid-cols-3 sm:grid-cols-6 gap-2 mb-3">
        {g.photos.map((p) => (
          <button key={p.id} data-testid={`recap-photo-${p.id}`} onClick={() => toggle(p.id)} className={`relative rounded-lg overflow-hidden ring-2 transition-shadow ${sel.includes(p.id) ? 'ring-[#B4247E]' : 'ring-transparent opacity-60'}`}>
            <img src={src(p.url)} alt="" className="w-full h-20 object-cover" />
            {sel.includes(p.id) && <span className="absolute top-1 right-1 bg-[#B4247E] text-white rounded-full p-0.5"><Check size={11} /></span>}
          </button>
        ))}
      </div>
      <textarea data-testid={`recap-note-${g.id}`} rows={3} value={note} onChange={(e) => setNote(e.target.value)} placeholder="A short thank-you note (optional)" className="w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
      <div className="flex gap-2 mt-3">
        <button data-testid={`recap-preview-${g.id}`} onClick={preview} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Eye size={14} /> Preview</button>
        <button data-testid={`recap-send-${g.id}`} onClick={send} disabled={busy} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send recap</button>
      </div>
      {msg && <p data-testid={`recap-msg-${g.id}`} className="text-[13px] text-[#241019]/70 mt-2">{msg}</p>}
      {html && <iframe data-testid={`recap-preview-frame-${g.id}`} title="Recap preview" srcDoc={html} className="w-full h-[520px] mt-4 rounded-xl border border-[#3B0A2E]/10 bg-white" />}
    </div>
  );
}

export function AdminRecaps() {
  const [rows, setRows] = useState(null);
  const [open, setOpen] = useState('');
  const load = useCallback(() => api.get('/admin/members/recaps').then(({ data }) => setRows(data)), []);
  useEffect(() => { load(); }, [load]);
  return (
    <div data-testid="admin-recaps" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 mt-6">
      <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-1">Gathering recap emails</h3>
      <p className="text-[13px] text-[#241019]/60 mb-5">Send members a recap with up to 6 approved photos and a link to the album. If no one sends it, a recap with the first 6 approved photos goes out automatically 3 days after the gathering.</p>
      {rows === null ? <p className="text-[#241019]/50">Loading…</p> : !rows.length ? <p className="text-[13.5px] text-[#241019]/50">No past gatherings yet.</p> : rows.map((g) => (
        <div key={g.id} data-testid={`recap-row-${g.id}`} className="border-t border-[#3B0A2E]/8 py-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div><p className="font-semibold text-[14px] text-[#3B0A2E]">{g.title}</p><p className="text-[12px] text-[#241019]/55">{g.date} · {g.photos.length} approved photo{g.photos.length === 1 ? '' : 's'}</p></div>
            {g.recap_sent_at ? <span data-testid={`recap-sent-${g.id}`} className="text-[12.5px] text-green-700 font-semibold">Sent {new Date(g.recap_sent_at).toLocaleDateString()}{g.recap_by === 'auto' ? ' (automatic)' : ''}{g.recap_count != null ? ` · ${g.recap_count} emails` : ''}</span>
              : <button data-testid={`recap-open-${g.id}`} onClick={() => setOpen(open === g.id ? '' : g.id)} className="text-[13px] font-semibold text-[#B4247E]">{open === g.id ? 'Close' : 'Prepare recap'}</button>}
          </div>
          {open === g.id && !g.recap_sent_at && <RecapEditor g={g} reload={load} />}
        </div>
      ))}
    </div>
  );
}
