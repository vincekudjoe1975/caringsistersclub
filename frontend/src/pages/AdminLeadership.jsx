import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { board as mockBoard } from '../mock/mock';
import { LeaderPhoto } from '../components/LeaderModal';
import { Loader2, Plus, GripVertical, Pencil, Trash2, Eye, EyeOff, UploadCloud, X, Users } from 'lucide-react';

const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';
const EMPTY = { name: '', role: '', group: 'board', intro: '', bio: '', photo_url: '', email: '', linkedin: '', visible: true };

function LeaderForm({ initial, onClose, onSaved }) {
  const { toast } = useToast();
  const [f, setF] = useState({ ...EMPTY, ...initial });
  const [busy, setBusy] = useState(false);
  const [up, setUp] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file); fd.append('category', 'board'); fd.append('title', f.name || 'Leader photo');
    setUp(true);
    try { const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setF((x) => ({ ...x, photo_url: data.url })); }
    catch (ex) { toast({ title: 'Upload failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setUp(false); }
  };
  const save = async (e) => {
    e.preventDefault(); setBusy(true);
    const body = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, f[k]]));
    try { initial.id ? await api.put(`/admin/leaders/${initial.id}`, body) : await api.post('/admin/leaders', body); toast({ title: 'Saved' }); onSaved(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} data-testid="leader-form" className="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] overflow-y-auto p-7 space-y-4 animate-[zoomIn_.25s_ease]">
        <div className="flex items-center justify-between"><h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{initial.id ? 'Edit team member' : 'Add team member'}</h3><button type="button" onClick={onClose}><X size={20} /></button></div>
        <div className="flex items-center gap-4">
          <div className="w-24 h-24 rounded-2xl overflow-hidden shrink-0"><LeaderPhoto m={f} /></div>
          <div className="space-y-2">
            <label data-testid="leader-photo-upload" className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] inline-flex items-center gap-1.5 cursor-pointer hover:border-[#B4247E]">
              {up ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />} {f.photo_url ? 'Replace photo' : 'Upload photo'}
              <input data-testid="leader-photo-input" type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
            </label>
            {f.photo_url && <button type="button" data-testid="leader-photo-remove" onClick={() => setF({ ...f, photo_url: '' })} className="block text-[12.5px] text-[#241019]/50 hover:text-red-600">Remove photo</button>}
          </div>
        </div>
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Full name *<input required value={f.name} onChange={set('name')} data-testid="leader-name-input" className={input} /></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Role / title<input value={f.role} onChange={set('role')} data-testid="leader-role-input" className={input} /></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Group
            <select value={f.group} onChange={set('group')} data-testid="leader-group-select" className={input}><option value="board">Board of Directors</option><option value="executive">Executive Team</option></select></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E] flex items-end gap-2 pb-2.5"><input type="checkbox" checked={f.visible} onChange={(e) => setF({ ...f, visible: e.target.checked })} data-testid="leader-visible-input" className="accent-[#B4247E] w-4 h-4" /> Show on website</label>
        </div>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Short intro (shown on hover and the card)<textarea rows={2} maxLength={400} value={f.intro} onChange={set('intro')} data-testid="leader-intro-input" className={`${input} resize-none`} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Full biography (shown when the card is opened)<textarea rows={8} maxLength={8000} value={f.bio} onChange={set('bio')} data-testid="leader-bio-input" className={`${input} resize-y`} /></label>
        <div className="grid sm:grid-cols-2 gap-4">
          <label className="text-[13px] font-semibold text-[#3B0A2E]">Email (optional)<input type="email" value={f.email} onChange={set('email')} data-testid="leader-email-input" className={input} /></label>
          <label className="text-[13px] font-semibold text-[#3B0A2E]">LinkedIn URL (optional)<input value={f.linkedin} onChange={set('linkedin')} data-testid="leader-linkedin-input" className={input} /></label>
        </div>
        <button type="submit" disabled={busy || up} data-testid="leader-save-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px] disabled:opacity-60 flex items-center gap-2">{busy && <Loader2 size={15} className="animate-spin" />} Save</button>
      </form>
    </div>
  );
}

export default function AdminLeadership() {
  const { toast } = useToast();
  const [rows, setRows] = useState(null);
  const [edit, setEdit] = useState(null);
  const [dragId, setDragId] = useState(null);
  const load = useCallback(() => api.get('/admin/leaders').then(({ data }) => setRows(data.items)), []);
  useEffect(() => { load(); }, [load]);
  const importDefaults = async () => {
    for (const m of mockBoard) await api.post('/admin/leaders', { ...EMPTY, name: m.name, role: m.role, intro: m.bio, bio: m.bio, photo_url: m.photo.startsWith('http') || m.photo.startsWith('/static/') ? m.photo : '' });
    toast({ title: 'Current team copied', description: 'You can now edit each member.' }); load();
  };
  const drop = async (targetId) => {
    if (!dragId || dragId === targetId) return;
    const ids = rows.map((r) => r.id); const from = ids.indexOf(dragId); ids.splice(from, 1); ids.splice(ids.indexOf(targetId) + (from <= ids.indexOf(targetId) ? 1 : 0), 0, dragId);
    setRows(ids.map((id) => rows.find((r) => r.id === id))); setDragId(null);
    await api.post('/admin/leaders/reorder', { ids });
  };
  const toggle = async (r) => { await api.put(`/admin/leaders/${r.id}`, { ...EMPTY, ...r, visible: !r.visible }); load(); };
  const del = async (r) => { if (window.confirm(`Remove ${r.name}?`)) { await api.delete(`/admin/leaders/${r.id}`); load(); } };
  if (rows === null) return <Loader2 className="animate-spin text-[#B4247E]" />;
  return (
    <div data-testid="admin-leadership">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div><h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Users size={20} className="text-[#B4247E]" /> Leadership page</h2>
          <p className="text-[13.5px] text-[#241019]/60">Add, edit and reorder the team on the public Leadership page. Drag cards to change the order.</p></div>
        <button data-testid="leader-add-btn" onClick={() => setEdit({})} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Plus size={15} /> Add member</button>
      </div>
      {!rows.length && (
        <div data-testid="leader-empty" className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8 text-center">
          <p className="text-[14px] text-[#241019]/65 mb-4">The website currently shows the built-in placeholder team. It's replaced as soon as you add your first member.</p>
          <button data-testid="leader-import-btn" onClick={importDefaults} className="rounded-full px-5 py-2.5 text-[13.5px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E]">Start from the current team</button>
        </div>
      )}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
        {rows.map((r) => (
          <div key={r.id} data-testid={`leader-row-${r.id}`} draggable onDragStart={() => setDragId(r.id)} onDragOver={(e) => e.preventDefault()} onDrop={() => drop(r.id)}
            className={`bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 transition-[opacity,transform] ${dragId === r.id ? 'opacity-50 scale-95' : ''} ${r.visible ? '' : 'opacity-60'}`}>
            <div className="h-44 relative"><LeaderPhoto m={r} /><span className="absolute top-2 left-2 bg-white/90 rounded-full p-1 cursor-grab text-[#3B0A2E]"><GripVertical size={15} /></span>
              {!r.visible && <span className="absolute top-2 right-2 bg-[#3B0A2E] text-white text-[11px] font-semibold rounded-full px-2.5 py-0.5">Hidden</span>}</div>
            <div className="p-4">
              <p className="font-serif text-[17px] text-[#3B0A2E] font-semibold leading-tight">{r.name}</p>
              <p className="text-[12.5px] text-[#B4247E] font-semibold">{r.role} · {r.group === 'executive' ? 'Executive' : 'Board'}</p>
              <div className="flex gap-3 mt-3 text-[#241019]/55">
                <button data-testid={`leader-edit-${r.id}`} onClick={() => setEdit(r)} className="hover:text-[#B4247E]" title="Edit"><Pencil size={15} /></button>
                <button data-testid={`leader-toggle-${r.id}`} onClick={() => toggle(r)} className="hover:text-[#B4247E]" title={r.visible ? 'Hide' : 'Show'}>{r.visible ? <EyeOff size={15} /> : <Eye size={15} />}</button>
                <button data-testid={`leader-delete-${r.id}`} onClick={() => del(r)} className="hover:text-red-600" title="Delete"><Trash2 size={15} /></button>
              </div>
            </div>
          </div>
        ))}
      </div>
      {edit && <LeaderForm initial={edit} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); }} />}
    </div>
  );
}
