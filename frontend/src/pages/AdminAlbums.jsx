import React, { useEffect, useState, useCallback } from 'react';
import { api, mediaSrc } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Plus, Pencil, Trash2, X, FolderOpen, Check } from 'lucide-react';

const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

function AlbumForm({ album, photos, onClose, onSaved }) {
  const { toast } = useToast();
  const [f, setF] = useState({ title: album.title || '', story: album.story || '', date: album.date || '', cover_id: album.cover_id || '' });
  const isNew = !album.key;
  const save = async (e) => {
    e.preventDefault();
    try { isNew ? await api.post('/admin/gallery-albums', f) : await api.put('/admin/gallery-albums', { key: album.key, ...f }); toast({ title: 'Album saved' }); onSaved(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const mine = photos.filter((p) => (album.photo_ids || []).includes(p.id));
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} data-testid="album-form" className="bg-white rounded-2xl max-w-2xl w-full max-h-[92vh] overflow-y-auto p-7 space-y-4 animate-[zoomIn_.25s_ease]">
        <div className="flex items-center justify-between"><h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{isNew ? 'New album' : 'Edit album'}</h3><button type="button" onClick={onClose}><X size={20} /></button></div>
        {!isNew && !album.manual && <p className="text-[12.5px] text-[#241019]/55">This album is built automatically from photos tagged "{album.title}". Leave the title blank to use the tag name.</p>}
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Title{isNew || album.manual ? ' *' : ''}<input data-testid="album-title-input" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} maxLength={150} required={isNew || album.manual} className={input} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">Date<input data-testid="album-date-input" type="date" value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} className={input} /></label>
        <label className="block text-[13px] font-semibold text-[#3B0A2E]">The story of this event<textarea data-testid="album-story-input" rows={5} value={f.story} onChange={(e) => setF({ ...f, story: e.target.value })} maxLength={4000} placeholder="What happened, who came, what it meant…" className={`${input} resize-y`} /></label>
        {mine.length > 0 && (
          <div><p className="text-[13px] font-semibold text-[#3B0A2E] mb-2">Cover photo</p>
            <div className="grid grid-cols-4 sm:grid-cols-6 gap-2">
              {mine.map((p) => (
                <button type="button" key={p.id} data-testid={`album-cover-${p.id}`} onClick={() => setF({ ...f, cover_id: p.id })} className={`relative rounded-lg overflow-hidden ring-2 ${f.cover_id === p.id ? 'ring-[#B4247E]' : 'ring-transparent'}`}>
                  <img src={mediaSrc(p.url)} alt="" className="w-full h-16 object-cover" />
                  {f.cover_id === p.id && <span className="absolute top-1 right-1 bg-[#B4247E] text-white rounded-full p-0.5"><Check size={10} /></span>}
                </button>
              ))}
            </div>
          </div>
        )}
        <button data-testid="album-save-btn" className="btn-magenta rounded-full px-8 py-3 font-semibold text-[14px]">Save album</button>
      </form>
    </div>
  );
}

export function useAlbums() {
  const [albums, setAlbums] = useState([]);
  const load = useCallback(() => api.get('/admin/gallery-albums').then(({ data }) => setAlbums(data.items)), []);
  useEffect(() => { load(); }, [load]);
  return [albums, load];
}

export function AdminAlbums({ albums, photos, reload }) {
  const [edit, setEdit] = useState(null);
  const del = async (a) => { if (window.confirm(`Delete the album "${a.title}"? Its photos stay in the gallery.`)) { await api.delete(`/admin/gallery-albums/${a.id}`); reload(); } };
  return (
    <div data-testid="admin-albums" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 mb-6">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div><h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold flex items-center gap-2"><FolderOpen size={18} className="text-[#B4247E]" /> Albums</h3>
          <p className="text-[12.5px] text-[#241019]/55">Albums are created automatically from each photo's Event/Program tag. You can also create your own and assign photos to them.</p></div>
        <button data-testid="album-new-btn" onClick={() => setEdit({})} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] flex items-center gap-1.5"><Plus size={14} /> New album</button>
      </div>
      {!albums.length ? <p data-testid="albums-admin-empty" className="text-[13px] text-[#241019]/50">No albums yet. Tag photos with an event or program, or create an album.</p> : (
        <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {albums.map((a) => (
            <div key={a.key} data-testid={`album-row-${a.slug}`} className="flex items-center gap-3 rounded-xl border border-[#3B0A2E]/8 p-2.5">
              {a.cover_url ? <img src={mediaSrc(a.cover_url)} alt="" className="w-14 h-14 rounded-lg object-cover" /> : <span className="w-14 h-14 rounded-lg" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }} />}
              <div className="flex-1 min-w-0"><p className="font-semibold text-[13.5px] text-[#3B0A2E] truncate">{a.title}</p><p className="text-[11.5px] text-[#241019]/55">{a.manual ? 'Custom' : a.tag_type === 'event' ? 'Event tag' : 'Program tag'} · {a.count} photo{a.count === 1 ? '' : 's'}{a.story ? '' : ' · no story yet'}</p></div>
              <button data-testid={`album-edit-${a.slug}`} onClick={() => setEdit(a)} className="text-[#241019]/50 hover:text-[#B4247E]"><Pencil size={15} /></button>
              {a.manual && <button data-testid={`album-delete-${a.slug}`} onClick={() => del(a)} className="text-[#241019]/50 hover:text-red-600"><Trash2 size={15} /></button>}
            </div>
          ))}
        </div>
      )}
      {edit && <AlbumForm album={edit} photos={photos} onClose={() => setEdit(null)} onSaved={() => { setEdit(null); reload(); }} />}
    </div>
  );
}
