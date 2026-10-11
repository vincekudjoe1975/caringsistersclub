import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Printer, Share2, EyeOff, Star, Upload, Trash2 } from 'lucide-react';
import { AnnualBody } from '../../../pages/AnnualReport';

const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const src = (u) => (u && u.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u);

export function AdminAnnual() {
  const { toast } = useToast();
  const [year, setYear] = useState(new Date().getFullYear());
  const [r, setR] = useState(null);
  const load = useCallback(() => api.get('/admin/members/annual', { params: { year } }).then(({ data }) => setR(data)), [year]);
  useEffect(() => { load(); }, [load]);
  const share = async () => { await api.post('/admin/members/annual/share', { year }); toast({ title: 'Annual summary shared with members' }); load(); };
  const unshare = async () => { await api.delete('/admin/members/annual/share', { params: { year } }); load(); };
  return (
    <div data-testid="admin-annual">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-5 flex flex-wrap items-center gap-3">
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold mr-auto">Annual summary</p>
        <select data-testid="annual-year-select" value={year} onChange={(e) => setYear(Number(e.target.value))} className={inputCls}>{[0, 1, 2, 3].map((i) => { const y = new Date().getFullYear() - i; return <option key={y}>{y}</option>; })}</select>
        <a data-testid="annual-open-print" href={`/annual-report?year=${year}`} target="_blank" rel="noreferrer" className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Printer size={14} /> Printable page</a>
        {r?.shared ? <button data-testid="annual-unshare-btn" onClick={unshare} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><EyeOff size={14} /> Hide from members</button>
          : <button data-testid="annual-share-btn" onClick={share} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Share2 size={14} /> Share with members</button>}
      </div>
      {r?.shared && <p data-testid="annual-shared-note" className="text-[12.5px] text-green-700 mb-3">Shared {new Date(r.shared.shared_at).toLocaleDateString()}. <button onClick={share} className="font-semibold underline">Update shared copy</button></p>}
      {r && <div className="bg-white rounded-2xl p-6 md:p-8 border border-[#3B0A2E]/8"><AnnualBody r={r} /></div>}
    </div>
  );
}

function SpotlightRow({ s, reload }) {
  const { toast } = useToast();
  const [story, setStory] = useState(s.story || '');
  const [photo, setPhoto] = useState(s.photo_url || '');
  const upload = async (file) => { if (!file) return; const fd = new FormData(); fd.append('file', file); const { data } = await api.post('/admin/members/spotlights/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setPhoto(data.url); };
  const save = async () => { await api.put(`/admin/members/spotlights/${s.id}`, { story, photo_url: photo }); toast({ title: 'Saved' }); reload(); };
  const publish = async () => {
    try { await api.put(`/admin/members/spotlights/${s.id}`, { story, photo_url: photo }); await api.post(`/admin/members/spotlights/${s.id}/publish`); toast({ title: 'Spotlight published', description: `${s.name} has been emailed.` }); reload(); }
    catch (ex) { toast({ title: 'Could not publish', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const BADGE = { draft: 'bg-amber-100 text-amber-800', invited: 'bg-blue-100 text-blue-800', submitted: 'bg-purple-100 text-purple-800', published: 'bg-green-100 text-green-800' };
  return (
    <div data-testid={`spotlight-row-${s.id}`} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
      <div className="flex items-center justify-between mb-3">
        <p className="font-semibold text-[#3B0A2E]">{s.name} · {new Date(s.month + '-15').toLocaleDateString(undefined, { month: 'long', year: 'numeric' })}</p>
        <span className="flex items-center gap-3"><span data-testid={`spotlight-status-${s.id}`} className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full ${BADGE[s.status]}`}>{s.status === 'invited' ? 'waiting for her story' : s.status}</span>
          <button data-testid={`spotlight-del-${s.id}`} onClick={async () => { if (window.confirm('Delete this spotlight?')) { await api.delete(`/admin/members/spotlights/${s.id}`); reload(); } }} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={14} /></button></span>
      </div>
      <div className="flex gap-4 items-start">
        <div className="w-24 shrink-0">
          {photo ? <img src={src(photo)} alt="" referrerPolicy="no-referrer" className="w-24 h-24 rounded-xl object-cover" /> : <div className="w-24 h-24 rounded-xl bg-[#F7EFE9]" />}
          <label className="mt-1 text-[11.5px] font-semibold text-[#B4247E] flex items-center gap-1 cursor-pointer"><Upload size={11} /> Photo<input data-testid={`spotlight-photo-${s.id}`} type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} /></label>
        </div>
        <textarea data-testid={`spotlight-story-${s.id}`} rows={5} value={story} onChange={(e) => setStory(e.target.value)} placeholder={s.status === 'invited' ? 'Waiting for her to share her story, or write it yourself…' : 'Her story…'} className={`${inputCls} flex-1`} />
      </div>
      <div className="flex gap-2 mt-3 justify-end">
        <button data-testid={`spotlight-save-${s.id}`} onClick={save} className="rounded-full px-4 py-2 text-[12.5px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E]">Save</button>
        {s.status !== 'published' && <button data-testid={`spotlight-publish-${s.id}`} onClick={publish} className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold">Approve & publish</button>}
      </div>
    </div>
  );
}

export function AdminSpotlight() {
  const { toast } = useToast();
  const now = new Date();
  const [rows, setRows] = useState([]);
  const [members, setMembers] = useState([]);
  const [f, setF] = useState({ user_id: '', month: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`, mode: 'staff', use_profile_photo: true });
  const load = useCallback(() => api.get('/admin/members/spotlights').then(({ data }) => setRows(data)), []);
  useEffect(() => { load(); api.get('/admin/members').then(({ data }) => setMembers(data.members.filter((m) => m.status === 'active'))); }, [load]);
  const create = async (e) => {
    e.preventDefault();
    try { await api.post('/admin/members/spotlights', f); toast({ title: f.mode === 'invite' ? 'Invitation emailed' : 'Spotlight draft created' }); load(); }
    catch (ex) { toast({ title: 'Could not create', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div className="grid lg:grid-cols-[1fr_1.6fr] gap-6" data-testid="admin-spotlight">
      <form onSubmit={create} data-testid="spotlight-form" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 space-y-3 self-start">
        <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Star size={17} className="text-[#CBA24B]" /> New Sisterhood Spotlight</p>
        <select data-testid="spotlight-sister" required value={f.user_id} onChange={(e) => setF({ ...f, user_id: e.target.value })} className={`${inputCls} w-full`}><option value="">Choose a sister…</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.name}</option>)}</select>
        <input data-testid="spotlight-month" type="month" value={f.month} onChange={(e) => setF({ ...f, month: e.target.value })} className={`${inputCls} w-full`} />
        <div className="flex gap-1">{[['staff', 'Staff write it'], ['invite', 'Invite her to share']].map(([k, l]) => <button type="button" key={k} data-testid={`spotlight-mode-${k}`} onClick={() => setF({ ...f, mode: k })} className={`flex-1 rounded-full py-1.5 text-[12.5px] font-semibold ${f.mode === k ? 'bg-[#3B0A2E] text-white' : 'bg-[#F7EFE9] text-[#3B0A2E]'}`}>{l}</button>)}</div>
        {f.mode === 'staff' && <label className="flex items-center gap-2 text-[13px] text-[#241019]/75"><input data-testid="spotlight-use-profile" type="checkbox" checked={f.use_profile_photo} onChange={(e) => setF({ ...f, use_profile_photo: e.target.checked })} className="accent-[#B4247E]" /> Start with her profile picture</label>}
        <p className="text-[12px] text-[#241019]/55">{f.mode === 'invite' ? 'She gets an email and a form in her portal to share a photo and story. You approve before it is featured.' : 'Then write her story and upload a photo below. Publishing features her on the portal home and emails her.'}</p>
        <button data-testid="spotlight-create-btn" className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold">Create</button>
      </form>
      <div className="space-y-3">
        {rows.map((s) => <SpotlightRow key={s.id} s={s} reload={load} />)}
        {!rows.length && <p className="text-[13.5px] text-[#241019]/50">No spotlights yet.</p>}
      </div>
    </div>
  );
}
