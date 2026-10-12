import React, { useEffect, useState } from 'react';
import { Trash2, Upload, Mail, Eye } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';

export const GalaExtras = ({ ev, toast }) => {
  const [sp, setSp] = useState(ev.sponsors || []);
  const [f, setF] = useState({ name: '', table: '' });
  const [th, setTh] = useState(null);
  const [preview, setPreview] = useState(false);
  useEffect(() => { api.get(`/admin/events/${ev.id}/gala-thanks`).then(({ data }) => setTh(data)).catch(() => {}); }, [ev.id]);
  const upload = async (file) => {
    if (!f.name.trim()) { toast({ title: 'Add the sponsor name first', variant: 'destructive' }); return; }
    const fd = new FormData(); fd.append('file', file); fd.append('name', f.name); fd.append('table', String(Number(f.table) || 0));
    try { const { data } = await api.post(`/admin/events/${ev.id}/sponsors`, fd); setSp([...sp, data]); setF({ name: '', table: '' }); } catch (ex) { toast({ title: 'Upload failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const del = (id) => api.delete(`/admin/events/${ev.id}/sponsors/${id}`).then(() => setSp(sp.filter((s) => s.id !== id)));
  const toggle = () => api.put(`/admin/events/${ev.id}/gala-thanks`, { enabled: !th.enabled }).then(({ data }) => setTh({ ...th, ...data }));
  const cls = 'rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px]';
  return (
    <div data-testid="gala-extras" className="mt-6 pt-4 border-t border-[#3B0A2E]/10 space-y-4">
      <div className="flex flex-wrap gap-2 text-[13.5px]">
        <a data-testid="gala-emcee-link" href={`/admin/gala/${ev.id}/emcee`} className="rounded-full px-4 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E]">Emcee paddle raise</a>
        <a data-testid="gala-auction-link" href={`/admin/auction/${ev.id}`} className="rounded-full px-4 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E]">Silent auction</a>
      </div>
      <div>
        <p className="text-[13px] font-semibold text-[#3B0A2E] mb-2">Sponsor logos</p>
        <div className="flex flex-wrap gap-2 items-center">
          <input data-testid="sponsor-name" placeholder="Sponsor name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={`${cls} flex-1 min-w-[140px]`} />
          <input data-testid="sponsor-table" type="number" min="0" placeholder="Table #" value={f.table} onChange={(e) => setF({ ...f, table: e.target.value })} className={`${cls} w-24`} />
          <label className="rounded-full px-4 py-2.5 font-semibold text-[13px] bg-[#3B0A2E] text-white cursor-pointer flex items-center gap-1.5"><Upload size={13} /> Logo<input data-testid="sponsor-file" type="file" accept="image/*" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} /></label>
        </div>
        <div className="flex flex-wrap gap-2 mt-2">{sp.map((s) => (
          <div key={s.id} data-testid={`sponsor-${s.id}`} className="flex items-center gap-2 rounded-xl border border-[#3B0A2E]/10 pl-2 pr-1 py-1"><img src={mediaSrc(s.logo)} alt={s.name} className="h-8 w-auto max-w-[80px] object-contain" /><span className="text-[12.5px]">{s.name}{s.table ? ` · T${s.table}` : ''}</span>
            <button data-testid={`sponsor-del-${s.id}`} onClick={() => del(s.id)} aria-label="Remove" className="w-8 h-8 flex items-center justify-center text-red-500"><Trash2 size={13} /></button></div>
        ))}</div>
      </div>
      {th && (
        <div data-testid="gala-thanks-box" className="text-[13.5px]">
          <p className="font-semibold text-[#3B0A2E] flex items-center gap-1.5"><Mail size={14} /> Morning-after thank-you email (9am ET)</p>
          <p className="text-[#241019]/60">{th.sent_at ? `Sent ${new Date(th.sent_at).toLocaleString()}` : `${th.recipients} recipient${th.recipients === 1 ? '' : 's'} so far`}</p>
          <div className="flex gap-2 mt-2">
            <button data-testid="gala-thanks-toggle" onClick={toggle} className={`rounded-full px-4 py-2 font-semibold ${th.enabled ? 'bg-emerald-50 text-emerald-700' : 'bg-gray-100 text-gray-500'}`}>{th.enabled ? 'On' : 'Off'}</button>
            <button data-testid="gala-thanks-preview" onClick={() => setPreview(!preview)} className="rounded-full px-4 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5"><Eye size={13} /> Preview</button>
          </div>
          {preview && <iframe data-testid="gala-thanks-frame" title="Thank-you preview" srcDoc={th.html} className="w-full h-[420px] mt-3 rounded-xl border border-[#3B0A2E]/10" />}
        </div>
      )}
    </div>
  );
};
