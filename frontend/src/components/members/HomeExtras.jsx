import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { PartyPopper, CalendarDays, MapPin, Loader2, Star, Upload } from 'lucide-react';

const longDate = (d) => new Date(d + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });

function RsvpForm({ g, onSaved }) {
  const mine = g.my_rsvp || {};
  const [f, setF] = useState({ response: mine.response || '', guests: mine.guests || 0, dietary: mine.dietary || '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const save = async () => {
    setBusy(true); setErr('');
    try { await api.post(`/members/gatherings/${g.id}/rsvp`, { ...f, guests: Number(f.guests) || 0 }); onSaved(); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not save RSVP.'); }
    finally { setBusy(false); }
  };
  if (!g.open) return <p className="text-[13px] text-[#F7EFE9]/70 mt-3">RSVPs are closed{mine.response ? `. You answered: ${mine.response}` : ''}.</p>;
  return (
    <div className="mt-4 space-y-3">
      <div className="flex flex-wrap gap-2">
        {[['yes', 'Yes, I\'ll be there'], ['maybe', 'Maybe'], ['no', 'Can\'t make it']].map(([v, l]) => (
          <button key={v} data-testid={`rsvp-${g.id}-${v}`} onClick={() => setF({ ...f, response: v })} className={`rounded-full px-4 py-2 text-[13px] font-semibold transition-colors ${f.response === v ? 'bg-[#CBA24B] text-[#3B0A2E]' : 'bg-white/10 text-[#F7EFE9] border border-white/20 hover:bg-white/20'}`}>{l}</button>
        ))}
      </div>
      {f.response && f.response !== 'no' && (
        <div className="flex flex-wrap gap-2">
          <label className="text-[12.5px] text-[#F7EFE9]/80 flex items-center gap-2">Guests <input data-testid={`rsvp-guests-${g.id}`} type="number" min="0" max="10" value={f.guests} onChange={(e) => setF({ ...f, guests: e.target.value })} className="w-16 rounded-full px-3 py-1.5 text-[13px] text-[#241019]" /></label>
          <input data-testid={`rsvp-dietary-${g.id}`} value={f.dietary} onChange={(e) => setF({ ...f, dietary: e.target.value })} placeholder="Dietary needs (optional)" className="flex-1 min-w-[160px] rounded-full px-4 py-1.5 text-[13px] text-[#241019]" />
        </div>
      )}
      <button data-testid={`rsvp-save-${g.id}`} onClick={save} disabled={!f.response || busy} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold flex items-center gap-1.5 disabled:opacity-50">{busy && <Loader2 size={13} className="animate-spin" />} {mine.response ? 'Update RSVP' : 'Send RSVP'}</button>
      {mine.response && <p data-testid={`rsvp-status-${g.id}`} className="text-[12.5px] text-[#F7EFE9]/75">You answered {mine.response}{mine.guests ? ` (+${mine.guests} guest${mine.guests === 1 ? '' : 's'})` : ''}.</p>}
      {err && <p className="text-[12.5px] text-red-200">{err}</p>}
    </div>
  );
}

export function Gatherings() {
  const [rows, setRows] = useState([]);
  const load = useCallback(() => api.get('/members/gatherings').then(({ data }) => setRows(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!rows.length) return null;
  return rows.slice(0, 1).map((g) => (
    <div key={g.id} data-testid={`gathering-card-${g.id}`} className="rounded-2xl p-6 mb-6 relative overflow-hidden csc-plum-deep-bg">
      <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><PartyPopper size={14} /> In-person gathering</p>
      <h3 className="font-serif text-[23px] text-[#F7EFE9] font-semibold">{g.title}</h3>
      <div className="flex flex-wrap gap-4 text-[13px] text-[#F7EFE9]/80 mt-1">
        <span className="flex items-center gap-1.5"><CalendarDays size={14} /> {longDate(g.date)}</span>
        {g.location && <span className="flex items-center gap-1.5"><MapPin size={14} /> {g.location}</span>}
        <span data-testid={`gathering-going-${g.id}`}>{g.going} going</span>
        {g.rsvp_deadline && <span>RSVP by {new Date(g.rsvp_deadline + 'T12:00:00').toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}</span>}
      </div>
      {g.details && <p className="text-[14px] text-[#F7EFE9]/85 mt-3 whitespace-pre-line">{g.details}</p>}
      <RsvpForm g={g} onSaved={load} />
    </div>
  ));
}

function InviteForm({ inv, me, onDone }) {
  const [story, setStory] = useState(inv.story || '');
  const [photo, setPhoto] = useState(inv.photo_url || me.picture || '');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try { const { data } = await api.post('/members/spotlight/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setPhoto(data.url); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Upload failed'); }
  };
  const submit = async () => {
    setBusy(true); setErr('');
    try { await api.post(`/members/spotlight/${inv.id}/submit`, { story, photo_url: photo }); onDone(); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not submit.'); setBusy(false); }
  };
  if (inv.status === 'submitted') return <div data-testid="spotlight-submitted" className="bg-white rounded-2xl p-5 mb-6 border border-[#CBA24B]/40 text-[14px] text-[#241019]/75">Thank you for sharing your story! Our team is reviewing it for your Sisterhood Spotlight.</div>;
  return (
    <div data-testid="spotlight-invite" className="bg-white rounded-2xl p-6 mb-6 border-2 border-[#CBA24B]/60">
      <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><Star size={14} /> You've been chosen</p>
      <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-3">Share your story for the Sisterhood Spotlight</h3>
      <div className="flex flex-wrap gap-4 items-start">
        <div className="w-28 shrink-0">
          {photo ? <img src={photo.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${photo}` : photo} alt="" referrerPolicy="no-referrer" className="w-28 h-28 rounded-2xl object-cover" /> : <div className="w-28 h-28 rounded-2xl bg-[#F7EFE9]" />}
          <label className="mt-2 text-[12px] font-semibold text-[#B4247E] flex items-center gap-1 cursor-pointer"><Upload size={12} /> Upload photo<input data-testid="spotlight-photo-input" type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} /></label>
        </div>
        <textarea data-testid="spotlight-story-input" rows={6} value={story} onChange={(e) => setStory(e.target.value)} placeholder="Tell your sisters about yourself: your story, what the Club means to you, a favourite memory…" className="flex-1 min-w-[220px] rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
      </div>
      {err && <p className="text-red-600 text-[13px] mt-2">{err}</p>}
      <button data-testid="spotlight-submit-btn" onClick={submit} disabled={busy || !story.trim()} className="btn-magenta rounded-full px-6 py-2.5 text-[13.5px] font-semibold mt-4 disabled:opacity-50">Submit my story</button>
    </div>
  );
}

export function Spotlight({ me }) {
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/members/spotlight').then(({ data }) => setD(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!d) return null;
  const s = d.spotlight;
  const src = (u) => (u && u.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u);
  return (
    <>
      {d.my_invite && <InviteForm inv={d.my_invite} me={me} onDone={load} />}
      {s && (
        <div data-testid="spotlight-card" className="bg-white rounded-2xl overflow-hidden mb-6 grid md:grid-cols-[260px_1fr] border border-[#3B0A2E]/8">
          {s.photo_url ? <img src={src(s.photo_url)} alt={s.name} referrerPolicy="no-referrer" className="w-full h-64 md:h-full object-cover" /> : <div className="h-40 md:h-full" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }} />}
          <div className="p-6 md:p-8">
            <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><Star size={14} /> Sisterhood Spotlight · {new Date(s.month + '-15').toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</p>
            <h3 data-testid="spotlight-name" className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-3">{s.name}</h3>
            <p data-testid="spotlight-story" className="text-[14.5px] text-[#241019]/80 leading-relaxed whitespace-pre-line">{s.story}</p>
          </div>
        </div>
      )}
    </>
  );
}
