import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { Camera, Upload, Trash2, ArrowLeft, X, Loader2, Cake, Check, Clock, ImageOff, Download, Gift } from 'lucide-react';

export const src = (u) => (u && u.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${u}` : u);
const longDate = (d) => new Date(d + 'T12:00:00').toLocaleDateString(undefined, { month: 'long', day: 'numeric', year: 'numeric' });
const multipart = { headers: { 'Content-Type': 'multipart/form-data' } };

function Uploader({ mid, onDone, isAdmin }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const upload = async (files) => {
    if (!files?.length) return;
    setBusy(true); setMsg('');
    let ok = 0;
    for (const f of files) {
      const fd = new FormData(); fd.append('file', f);
      try { await api.post(`/members/albums/${mid}/photos`, fd, multipart); ok += 1; } catch (ex) { setMsg(ex?.response?.data?.detail || 'Some photos could not be uploaded.'); }
    }
    setBusy(false);
    if (ok && !isAdmin) api.post(`/members/albums/${mid}/photos/done`).catch(() => {});
    if (ok) setMsg(isAdmin ? `${ok} photo${ok === 1 ? '' : 's'} added.` : `Thank you! ${ok} photo${ok === 1 ? '' : 's'} sent for staff review.`);
    onDone();
  };
  return (
    <div className="flex flex-wrap items-center gap-3">
      <label data-testid="album-upload-btn" className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2 cursor-pointer">
        {busy ? <Loader2 size={15} className="animate-spin" /> : <Upload size={15} />} Add photos
        <input data-testid="album-upload-input" type="file" accept="image/*" multiple className="hidden" disabled={busy} onChange={(e) => upload(Array.from(e.target.files || []))} />
      </label>
      {msg && <p data-testid="album-upload-msg" className="text-[13px] text-[#241019]/70">{msg}</p>}
    </div>
  );
}

function Album({ mid, me, onBack }) {
  const [d, setD] = useState(null);
  const [open, setOpen] = useState(null);
  const load = useCallback(() => api.get(`/members/albums/${mid}`).then(({ data }) => setD(data)), [mid]);
  useEffect(() => { load(); }, [load]);
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  const del = async (p) => { if (window.confirm(me.is_admin ? 'Remove this photo?' : 'Withdraw this photo?')) { await api.delete(`/members/gathering-photos/${p.id}`); setOpen(null); load(); } };
  return (
    <div data-testid="album-view">
      <button data-testid="album-back" onClick={onBack} className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-1 mb-3"><ArrowLeft size={14} /> All albums</button>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div><h2 className="font-serif text-[26px] text-[#3B0A2E] font-semibold">{d.gathering.title}</h2><p className="text-[13px] text-[#241019]/60">{longDate(d.gathering.date)}{d.gathering.location ? ` · ${d.gathering.location}` : ''}</p></div>
        <div className="flex flex-wrap items-center gap-3">
          {d.photos.some((p) => p.status === 'approved') && <a data-testid="album-download-zip" href={`${process.env.REACT_APP_BACKEND_URL}/api/members/albums/${mid}/download`} className="rounded-full px-5 py-2.5 text-[13.5px] font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-2 hover:border-[#B4247E] transition-colors"><Download size={15} /> Download album</a>}
          {d.can_upload && <Uploader mid={mid} onDone={load} isAdmin={me.is_admin} />}
        </div>
      </div>
      {!d.photos.length && <p data-testid="album-empty" className="text-[#241019]/60 py-10 text-center">No photos yet. Share your favourite moments from this gathering.</p>}
      <div className="columns-2 md:columns-3 gap-3 [&>*]:mb-3">
        {d.photos.map((p) => (
          <button key={p.id} data-testid={`album-photo-${p.id}`} onClick={() => setOpen(p)} className="relative block w-full rounded-xl overflow-hidden group">
            <img src={src(p.url)} alt={p.caption || 'Gathering photo'} className={`w-full object-cover transition-transform duration-500 group-hover:scale-[1.03] ${p.status === 'pending' ? 'opacity-60' : ''}`} />
            {p.status === 'pending' && <span data-testid={`album-pending-${p.id}`} className="absolute top-2 left-2 bg-white/90 text-[#3B0A2E] text-[11px] font-semibold rounded-full px-2.5 py-0.5 flex items-center gap-1"><Clock size={11} /> Awaiting review</span>}
          </button>
        ))}
      </div>
      {open && (
        <div data-testid="album-lightbox" className="fixed inset-0 z-50 bg-black/85 flex flex-col items-center justify-center p-4" onClick={() => setOpen(null)}>
          <img src={src(open.url)} alt="" className="max-h-[80vh] max-w-full rounded-xl" onClick={(e) => e.stopPropagation()} />
          <div className="flex items-center gap-4 mt-4 text-white/85 text-[13px]" onClick={(e) => e.stopPropagation()}>
            <span>Shared by {open.uploader_name}</span>
            {open.status === 'approved' && <a data-testid="album-photo-download" href={`${src(open.url)}?download=1`} className="flex items-center gap-1 text-[#CBA24B]"><Download size={14} /> Download</a>}
            {(me.is_admin || (open.mine && open.status === 'pending')) && <button data-testid="album-photo-delete" onClick={() => del(open)} className="flex items-center gap-1 text-red-300"><Trash2 size={14} /> {me.is_admin ? 'Remove' : 'Withdraw'}</button>}
            <button data-testid="album-lightbox-close" onClick={() => setOpen(null)}><X size={20} /></button>
          </div>
        </div>
      )}
    </div>
  );
}

export function PhotoAlbums({ me }) {
  const [rows, setRows] = useState(null);
  const [mid, setMid] = useState(null);
  useEffect(() => { if (!mid) api.get('/members/albums').then(({ data }) => setRows(data)).catch(() => setRows([])); }, [mid]);
  if (mid) return <Album mid={mid} me={me} onBack={() => setMid(null)} />;
  if (rows === null) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div>
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2"><Camera size={20} className="text-[#CBA24B]" /> Gathering photos</h2>
      <p className="text-[13.5px] text-[#241019]/60 mb-6">Private albums from our in-person gatherings. Photos shared by sisters appear after a quick staff review.</p>
      {!rows.length && <p data-testid="albums-empty" className="text-[#241019]/60">Albums open after our first in-person gathering.</p>}
      <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5" data-testid="albums-grid">
        {rows.map((a) => (
          <button key={a.id} data-testid={`album-tile-${a.id}`} onClick={() => setMid(a.id)} className="text-left bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 hover:-translate-y-1 transition-transform duration-300">
            {a.cover ? <img src={src(a.cover)} alt={a.title} className="w-full h-48 object-cover" /> : <div className="h-48 flex items-center justify-center" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><ImageOff className="text-white/40" size={30} /></div>}
            <div className="p-4"><p className="font-serif text-[18px] text-[#3B0A2E] font-semibold">{a.title}</p><p className="text-[12.5px] text-[#241019]/60">{longDate(a.date)} · <span data-testid={`album-count-${a.id}`}>{a.count}</span> photo{a.count === 1 ? '' : 's'}</p></div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function BirthdayToday({ me }) {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get('/members/birthdays/today').then(({ data }) => setRows(data)).catch(() => {}); }, []);
  if (!rows.length) return null;
  const mine = rows.some((r) => r.user_id === me.user_id);
  const others = rows.filter((r) => r.user_id !== me.user_id).map((r) => r.name.split(' ')[0]);
  return (
    <div data-testid="birthday-today-banner" className="rounded-2xl p-6 mb-6 relative overflow-hidden flex items-center gap-5" style={{ background: 'linear-gradient(120deg,#CBA24B,#e6c77a)' }}>
      <span className="w-14 h-14 rounded-2xl bg-[#3B0A2E] flex items-center justify-center shrink-0"><Cake className="text-[#CBA24B]" size={26} /></span>
      <div>
        <p className="eyebrow text-[#3B0A2E]/70 mb-0.5">Today</p>
        <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{mine ? `Happy Birthday, ${(me.name || 'Sister').split(' ')[0]}! Your sisters are celebrating you.` : `Happy Birthday, ${others.join(' & ')}!`}</h3>
        {mine && others.length > 0 && <p className="text-[13.5px] text-[#3B0A2E]/80">You share your birthday with {others.join(' & ')}.</p>}
        {!mine && <p className="text-[13.5px] text-[#3B0A2E]/80">Send your wishes in the birthdays card below.</p>}
      </div>
    </div>
  );
}

export function AdminGatheringPhotos() {
  const [rows, setRows] = useState(null);
  const load = useCallback(() => api.get('/admin/members/gathering-photos').then(({ data }) => setRows(data)), []);
  useEffect(() => { load(); }, [load]);
  const approve = async (id) => { await api.post(`/admin/members/gathering-photos/${id}/approve`); load(); };
  const reject = async (id) => { await api.delete(`/members/gathering-photos/${id}`); load(); };
  const [ps, setPs] = useState(null);
  useEffect(() => { api.get('/admin/members/photo-settings').then(({ data }) => setPs(data)); }, []);
  const savePs = async (k, v) => { const n = { ...ps, [k]: v }; setPs(n); await api.put('/admin/members/photo-settings', n); };
  return (
    <div data-testid="admin-gathering-photos" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
      <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-1">Gathering photos awaiting review</h3>
      <p className="text-[13px] text-[#241019]/60 mb-5">Photos sisters share go live in the private portal albums once approved. Staff uploads (from the portal Photos tab) appear right away.</p>
      {ps && (
        <div className="flex flex-wrap gap-4 mb-6 text-[13px]">
          <label className="flex items-center gap-2 text-[#3B0A2E] font-semibold">Staff alerts
            <select data-testid="photo-settings-staff" value={ps.staff_alert} onChange={(e) => savePs('staff_alert', e.target.value)} className="rounded-lg border border-[#3B0A2E]/15 px-3 py-1.5 font-normal">
              <option value="both">Instantly + daily summary</option><option value="instant">Instantly per upload batch</option><option value="daily">Daily summary only</option><option value="off">Off</option>
            </select></label>
          <label className="flex items-center gap-2 text-[#3B0A2E] font-semibold">Tell the sister when approved
            <select data-testid="photo-settings-approve" value={ps.approve_notice} onChange={(e) => savePs('approve_notice', e.target.value)} className="rounded-lg border border-[#3B0A2E]/15 px-3 py-1.5 font-normal">
              <option value="gathering">One email per gathering</option><option value="each">An email for every photo</option><option value="off">Off</option>
            </select></label>
        </div>
      )}
      {rows === null ? <p className="text-[#241019]/50">Loading…</p> : !rows.length ? <p data-testid="gphotos-empty" className="text-[13.5px] text-[#241019]/50">Nothing waiting for review.</p> : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {rows.map((p) => (
            <div key={p.id} data-testid={`gphoto-${p.id}`} className="rounded-xl overflow-hidden border border-[#3B0A2E]/10">
              <img src={src(p.url)} alt="" className="w-full h-40 object-cover" />
              <div className="p-3"><p className="text-[12.5px] font-semibold text-[#3B0A2E] truncate">{p.gathering_title}</p><p className="text-[11.5px] text-[#241019]/55">by {p.uploader_name}</p>
                <div className="flex gap-2 mt-2">
                  <button data-testid={`gphoto-approve-${p.id}`} onClick={() => approve(p.id)} className="btn-magenta rounded-full px-3 py-1 text-[12px] font-semibold flex items-center gap-1"><Check size={12} /> Approve</button>
                  <button data-testid={`gphoto-reject-${p.id}`} onClick={() => reject(p.id)} className="rounded-full px-3 py-1 text-[12px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1"><X size={12} /> Remove</button>
                </div></div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function AdminPhotoControl({ m, reload }) {
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    try { await api.post(`/admin/members/${m.user_id}/photo`, fd, multipart); reload(); } catch (ex) { window.alert(ex?.response?.data?.detail || 'Upload failed'); }
  };
  return (
    <span className="flex items-center gap-1.5 shrink-0">
      <label title="Replace photo" data-testid={`admin-photo-upload-${m.user_id}`} className="text-[#B4247E] cursor-pointer"><Camera size={14} /><input data-testid={`admin-photo-input-${m.user_id}`} type="file" accept="image/*" className="hidden" onChange={(e) => upload(e.target.files?.[0])} /></label>
      {m.picture && <button title="Remove photo" data-testid={`admin-photo-remove-${m.user_id}`} onClick={async () => { if (window.confirm('Remove her profile photo?')) { await api.delete(`/admin/members/${m.user_id}/photo`); reload(); } }} className="text-[#241019]/40 hover:text-red-600"><ImageOff size={14} /></button>}
    </span>
  );
}

export function MyWishes({ me }) {
  const [w, setW] = useState(null);
  const month = new Date().getMonth() + 1;
  useEffect(() => { if (me.profile?.birthday_month === month) api.get(`/members/birthdays/${me.user_id}/wall`).then(({ data }) => setW(data)).catch(() => {}); }, [me, month]);
  if (!w) return null;
  return (
    <a data-testid="my-wishes-card" href={`/birthday-wishes/${me.user_id}`} className="block rounded-2xl p-6 mb-6 bg-white border-2 border-[#CBA24B]/60 hover:-translate-y-0.5 transition-transform">
      <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><Gift size={14} /> Your birthday month</p>
      <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold">Your sisters' wishes for you</h3>
      <p className="text-[13.5px] text-[#241019]/70 mt-1"><span data-testid="my-wishes-count">{w.wishes.length}</span> wish{w.wishes.length === 1 ? '' : 'es'} so far. Open your festive card to read, save or print it.</p>
    </a>
  );
}
