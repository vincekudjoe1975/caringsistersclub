import React, { useEffect, useState, useCallback } from 'react';
import { api, mediaSrc } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { AdminAlbums, useAlbums } from './AdminAlbums';
import { Loader2, UploadCloud, GripVertical, Pencil, Trash2, Eye, EyeOff, X, Images } from 'lucide-react';

const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

function TagFields({ f, setF, programs, events, albums = [] }) {
  const manual = albums.filter((a) => a.manual);
  const opts = f.tag_type === 'program' ? programs.map((p) => [p.slug, p.title]) : f.tag_type === 'event' ? events.map((e) => [e.id, e.title]) : [];
  return (
    <div className="grid sm:grid-cols-2 gap-4">
      <label className="text-[13px] font-semibold text-[#3B0A2E]">Tag
        <select data-testid="gallery-tag-type" value={f.tag_type} onChange={(e) => setF({ ...f, tag_type: e.target.value, tag_ref: '', tag_label: '' })} className={input}>
          <option value="">No tag</option><option value="event">Event</option><option value="program">Program</option>
        </select></label>
      {f.tag_type && (
        <label className="text-[13px] font-semibold text-[#3B0A2E]">{f.tag_type === 'event' ? 'Which event' : 'Which program'}
          <select data-testid="gallery-tag-ref" value={f.tag_ref || (f.tag_label ? '__custom' : '')} onChange={(e) => { const o = opts.find(([v]) => v === e.target.value); setF({ ...f, tag_ref: o ? o[0] : '', tag_label: o ? o[1] : f.tag_label }); }} className={input}>
            <option value="">Choose…</option>{opts.map(([v, l]) => <option key={v} value={v}>{l}</option>)}<option value="__custom">Other (type a name)</option>
          </select>
          {(!f.tag_ref) && <input data-testid="gallery-tag-label" value={f.tag_label} onChange={(e) => setF({ ...f, tag_label: e.target.value })} placeholder={f.tag_type === 'event' ? 'e.g. 2025 Gala' : 'e.g. Mentorship Circles'} className={input} />}
        </label>
      )}
      {manual.length > 0 && (
        <label className="text-[13px] font-semibold text-[#3B0A2E] sm:col-span-2">Album
          <select data-testid="gallery-album-select" value={f.album_key || ''} onChange={(e) => setF({ ...f, album_key: e.target.value })} className={input}>
            <option value="">Automatic (by tag)</option>{manual.map((a) => <option key={a.key} value={a.key}>{a.title}</option>)}
          </select></label>
      )}
    </div>
  );
}

function EditDialog({ item, programs, events, albums, onClose, onSaved }) {
  const [f, setF] = useState({ title: item.title || '', description: item.description || '', tag_type: item.tag_type || '', tag_label: item.tag_label || '', tag_ref: item.tag_ref || '', hidden: !!item.hidden, album_key: item.album_key || '' });
  const save = async (e) => { e.preventDefault(); await api.put(`/admin/gallery/${item.id}`, f); onSaved(); };
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} data-testid="gallery-edit-form" className="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] overflow-y-auto p-7 space-y-4 animate-[zoomIn_.25s_ease]">
        <div className="flex items-center justify-between"><h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Edit photo</h3><button type="button" onClick={onClose}><X size={20} /></button></div>
        <img src={mediaSrc(item.url)} alt="" className="w-full max-h-64 object-contain rounded-xl bg-[#F7EFE9]" />
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Title<input data-testid="gallery-edit-title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} maxLength={150} className={input} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Description<textarea data-testid="gallery-edit-desc" rows={4} value={f.description} onChange={(e) => setF({ ...f, description: e.target.value })} maxLength={2000} className={`${input} resize-y`} /></label>
        <TagFields f={f} setF={setF} programs={programs} events={events} albums={albums} />
        <label className="flex items-center gap-2 text-[13.5px] text-[#3B0A2E]"><input type="checkbox" checked={f.hidden} onChange={(e) => setF({ ...f, hidden: e.target.checked })} data-testid="gallery-edit-hidden" className="accent-[#B4247E] w-4 h-4" /> Hide from the public gallery</label>
        <button data-testid="gallery-edit-save" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px]">Save</button>
      </form>
    </div>
  );
}

export default function AdminGallery() {
  const { toast } = useToast();
  const [rows, setRows] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [events, setEvents] = useState([]);
  const [files, setFiles] = useState([]);
  const [meta, setMeta] = useState({ title: '', description: '', tag_type: '', tag_label: '', tag_ref: '', album_key: '' });
  const [albums, reloadAlbums] = useAlbums();
  const [busy, setBusy] = useState('');
  const [edit, setEdit] = useState(null);
  const [dragId, setDragId] = useState(null);
  const load = useCallback(() => api.get('/admin/gallery').then(({ data }) => setRows(data.items)), []);
  useEffect(() => {
    load();
    api.get('/admin/programs').then(({ data }) => setPrograms(data.items || data || [])).catch(() => {});
    api.get('/admin/events').then(({ data }) => setEvents(data.items || [])).catch(() => {});
  }, [load]);
  const upload = async (e) => {
    e.preventDefault();
    if (!files.length) { toast({ title: 'Choose one or more photos', variant: 'destructive' }); return; }
    let ok = 0;
    for (let i = 0; i < files.length; i += 1) {
      setBusy(`Uploading ${i + 1} of ${files.length}…`);
      const fd = new FormData(); fd.append('file', files[i]); fd.append('category', 'gallery'); if (meta.title) fd.append('title', meta.title);
      try {
        const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
        if (meta.description || meta.tag_type || meta.album_key) await api.put(`/admin/gallery/${data.id}`, { ...meta, hidden: false });
        ok += 1;
      } catch (ex) { toast({ title: `${files[i].name} failed`, description: ex?.response?.data?.detail, variant: 'destructive' }); }
    }
    setBusy(''); setFiles([]); e.target.reset?.(); reloadAlbums();
    if (ok) toast({ title: `${ok} photo${ok === 1 ? '' : 's'} added` });
    load();
  };
  const drop = async (targetId) => {
    if (!dragId || dragId === targetId) return;
    const ids = rows.map((r) => r.id); const from = ids.indexOf(dragId); ids.splice(from, 1); ids.splice(ids.indexOf(targetId) + (from <= ids.indexOf(targetId) ? 1 : 0), 0, dragId);
    setRows(ids.map((id) => rows.find((r) => r.id === id))); setDragId(null);
    await api.post('/admin/gallery/reorder', { ids });
  };
  const toggle = async (r) => { await api.put(`/admin/gallery/${r.id}`, { title: r.title || '', description: r.description || '', tag_type: r.tag_type || '', tag_label: r.tag_label || '', tag_ref: r.tag_ref || '', album_key: r.album_key || '', hidden: !r.hidden }); load(); reloadAlbums(); };
  const del = async (r) => { if (window.confirm('Delete this photo?')) { await api.delete(`/media/${r.id}`); load(); reloadAlbums(); } };
  return (
    <div data-testid="admin-gallery" className="grid lg:grid-cols-[360px_1fr] gap-8 items-start">
      <form onSubmit={upload} className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8 space-y-4 lg:sticky lg:top-6">
        <h2 className="font-serif text-[20px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Images size={18} className="text-[#B4247E]" /> Add gallery photos</h2>
        <label className="block border-2 border-dashed border-[#3B0A2E]/20 rounded-xl p-6 text-center cursor-pointer hover:border-[#B4247E] transition-colors">
          <UploadCloud className="mx-auto text-[#B4247E] mb-2" size={28} />
          <span data-testid="gallery-files-label" className="text-[13px] text-[#241019]/70 block">{files.length ? `${files.length} photo${files.length === 1 ? '' : 's'} selected` : 'Choose one or more images'}</span>
          <input data-testid="gallery-upload-input" type="file" accept="image/*" multiple className="hidden" onChange={(e) => setFiles(Array.from(e.target.files || []))} />
        </label>
        <p className="text-[12px] text-[#241019]/55">These details apply to every photo in this upload. You can edit each photo afterwards.</p>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Title<input data-testid="gallery-upload-title" value={meta.title} onChange={(e) => setMeta({ ...meta, title: e.target.value })} maxLength={150} className={input} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Description<textarea data-testid="gallery-upload-desc" rows={3} value={meta.description} onChange={(e) => setMeta({ ...meta, description: e.target.value })} maxLength={2000} className={`${input} resize-y`} /></label>
        <TagFields f={meta} setF={setMeta} programs={programs} events={events} albums={albums} />
        <button type="submit" disabled={!!busy} data-testid="gallery-upload-btn" className="btn-magenta rounded-full w-full py-3 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">{busy ? <><Loader2 className="animate-spin" size={16} /> {busy}</> : <><UploadCloud size={16} /> Upload</>}</button>
      </form>
      <div>
        <AdminAlbums albums={albums} photos={rows || []} reload={reloadAlbums} />
        {rows === null ? <Loader2 className="animate-spin text-[#B4247E]" /> : !rows.length ? (
          <div data-testid="gallery-admin-empty" className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8 text-[#241019]/55">No photos yet. The public gallery shows the built-in sample photos until you upload your own.</div>
        ) : (
          <>
            <p className="text-[12.5px] text-[#241019]/55 mb-3">Drag photos to change their order on the public gallery.</p>
            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
              {rows.map((r) => (
                <div key={r.id} data-testid={`gallery-row-${r.id}`} draggable onDragStart={() => setDragId(r.id)} onDragOver={(e) => e.preventDefault()} onDrop={() => drop(r.id)}
                  className={`bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 transition-[opacity,transform] ${dragId === r.id ? 'opacity-50 scale-95' : ''} ${r.hidden ? 'opacity-60' : ''}`}>
                  <div className="h-44 relative"><img src={mediaSrc(r.url)} alt="" className="w-full h-full object-cover" />
                    <span className="absolute top-2 left-2 bg-white/90 rounded-full p-1 cursor-grab text-[#3B0A2E]"><GripVertical size={15} /></span>
                    {r.hidden && <span className="absolute top-2 right-2 bg-[#3B0A2E] text-white text-[11px] font-semibold rounded-full px-2.5 py-0.5">Hidden</span>}
                    {r.tag_label && <span className="absolute bottom-2 left-2 bg-white/90 text-[#3B0A2E] text-[11px] font-semibold rounded-full px-2.5 py-0.5">{r.tag_label}</span>}</div>
                  <div className="p-4">
                    <p className="font-semibold text-[14px] text-[#3B0A2E] truncate">{r.title || <span className="text-[#241019]/40 font-normal">No title</span>}</p>
                    <p className="text-[12.5px] text-[#241019]/55 line-clamp-2 min-h-[2.4em]">{r.description}</p>
                    <div className="flex gap-3 mt-2 text-[#241019]/55">
                      <button data-testid={`gallery-edit-${r.id}`} onClick={() => setEdit(r)} className="hover:text-[#B4247E]" title="Edit"><Pencil size={15} /></button>
                      <button data-testid={`gallery-toggle-${r.id}`} onClick={() => toggle(r)} className="hover:text-[#B4247E]" title={r.hidden ? 'Show' : 'Hide'}>{r.hidden ? <Eye size={15} /> : <EyeOff size={15} />}</button>
                      <button data-testid={`gallery-delete-${r.id}`} onClick={() => del(r)} className="hover:text-red-600" title="Delete"><Trash2 size={15} /></button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
      </div>
      {edit && <EditDialog item={edit} programs={programs} events={events} albums={albums} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); load(); reloadAlbums(); }} />}
    </div>
  );
}
