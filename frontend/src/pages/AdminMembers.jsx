import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Check, X, Mail, Trash2, Megaphone, UploadCloud, Loader2, PauseCircle, PlayCircle } from 'lucide-react';
import { fmtDate } from '../components/members/fmt';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';
const Box = ({ title, children, testid }) => (
  <div data-testid={testid} className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
    <h3 className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-4">{title}</h3>{children}
  </div>
);

function Applications({ rows, act }) {
  if (!rows.length) return <p className="text-[13.5px] text-[#241019]/50">No applications waiting.</p>;
  return rows.map((m) => (
    <div key={m.user_id} data-testid={`application-${m.user_id}`} className="border border-[#3B0A2E]/8 rounded-xl p-4 mb-3">
      <div className="flex flex-wrap justify-between gap-3">
        <div><p className="font-semibold text-[#3B0A2E]">{m.name}</p><p className="text-[12.5px] text-[#241019]/55">{m.email} · {m.phone || 'no phone'} · {m.city}</p></div>
        <div className="flex gap-2">
          <button data-testid={`approve-${m.user_id}`} onClick={() => act(m.user_id, 'approve')} className="btn-magenta rounded-full px-4 py-1.5 text-[13px] font-semibold flex items-center gap-1"><Check size={14} /> Approve</button>
          <button data-testid={`decline-${m.user_id}`} onClick={() => act(m.user_id, 'decline')} className="rounded-full px-4 py-1.5 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1"><X size={14} /> Decline</button>
        </div>
      </div>
      <p className="text-[13px] text-[#241019]/75 mt-2"><b>Referred by:</b> {m.application.referred_by}</p>
      {m.application.why && <p className="text-[13px] text-[#241019]/75 mt-1 whitespace-pre-line">{m.application.why}</p>}
      <p className="text-[11.5px] text-[#241019]/40 mt-1">Applied {fmtDate(m.application.submitted_at)}</p>
    </div>
  ));
}

function Roster({ rows, act }) {
  if (!rows.length) return <p className="text-[13.5px] text-[#241019]/50">No members yet.</p>;
  return (
    <div className="divide-y divide-[#3B0A2E]/8" data-testid="member-roster">
      {rows.map((m) => (
        <div key={m.user_id} className="py-2.5 flex items-center justify-between gap-3">
          <div className="min-w-0"><p className="text-[14px] font-semibold text-[#3B0A2E] truncate">{m.name} {m.status !== 'active' && <span className="text-[11px] uppercase text-[#B4247E] ml-1">{m.status}</span>}</p><p className="text-[12px] text-[#241019]/50 truncate">{m.email}</p></div>
          {m.status === 'active'
            ? <button data-testid={`suspend-${m.user_id}`} onClick={() => act(m.user_id, 'suspend')} className="text-[12.5px] text-[#241019]/55 hover:text-red-600 flex items-center gap-1"><PauseCircle size={14} /> Pause</button>
            : <button data-testid={`reinstate-${m.user_id}`} onClick={() => act(m.user_id, 'reinstate')} className="text-[12.5px] text-[#B4247E] flex items-center gap-1"><PlayCircle size={14} /> Activate</button>}
        </div>
      ))}
    </div>
  );
}

function Invites({ invites, reload, toast }) {
  const [f, setF] = useState({ email: '', name: '' });
  const send = async (e) => {
    e.preventDefault();
    try { await api.post('/admin/members/invite', f); setF({ email: '', name: '' }); toast({ title: 'Invitation sent' }); reload(); }
    catch (ex) { toast({ title: 'Could not invite', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <>
      <form onSubmit={send} className="flex flex-wrap gap-2 mb-4">
        <input data-testid="invite-name" placeholder="Name" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} className={`${inputCls} flex-1 min-w-[140px]`} />
        <input data-testid="invite-email" placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} className={`${inputCls} flex-1 min-w-[180px]`} />
        <button data-testid="invite-send-btn" className="btn-magenta rounded-full px-5 py-2 text-[13.5px] font-semibold flex items-center gap-1.5"><Mail size={14} /> Invite</button>
      </form>
      {invites.map((i) => (
        <div key={i.email} className="flex items-center justify-between text-[13px] py-1.5">
          <span className="text-[#241019]/75 truncate">{i.name ? `${i.name} · ` : ''}{i.email}</span>
          <span className="flex items-center gap-2 shrink-0">
            <span className={i.status === 'accepted' ? 'text-green-700' : 'text-[#B4247E]'}>{i.status}</span>
            {i.status === 'pending' && <button data-testid={`invite-cancel-${i.email}`} onClick={async () => { await api.delete(`/admin/members/invite/${encodeURIComponent(i.email)}`); reload(); }} className="text-[#241019]/40 hover:text-red-600"><Trash2 size={14} /></button>}
          </span>
        </div>
      ))}
    </>
  );
}

function AnnouncementForm({ toast }) {
  const [f, setF] = useState({ title: '', body: '', pinned: false, email_members: false });
  const [items, setItems] = useState([]);
  const load = useCallback(() => api.get('/members/announcements').then(({ data }) => setItems(data)), []);
  useEffect(() => { load(); }, [load]);
  const post = async (e) => {
    e.preventDefault();
    try { await api.post('/admin/members/announcements', f); setF({ title: '', body: '', pinned: false, email_members: false }); toast({ title: 'Announcement posted' }); load(); }
    catch (ex) { toast({ title: 'Could not post', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <>
      <form onSubmit={post} className="space-y-3 mb-5">
        <input data-testid="announce-title" placeholder="Title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inputCls} />
        <textarea data-testid="announce-body" rows={4} placeholder="Message to members" value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} className={inputCls} />
        <div className="flex flex-wrap items-center gap-5 text-[13.5px] text-[#241019]/75">
          <label className="flex items-center gap-2"><input data-testid="announce-pinned" type="checkbox" checked={f.pinned} onChange={(e) => setF({ ...f, pinned: e.target.checked })} className="accent-[#B4247E]" /> Pin to top</label>
          <label className="flex items-center gap-2"><input data-testid="announce-email" type="checkbox" checked={f.email_members} onChange={(e) => setF({ ...f, email_members: e.target.checked })} className="accent-[#B4247E]" /> Also email all members</label>
          <button data-testid="announce-post-btn" className="btn-magenta rounded-full px-5 py-2 font-semibold ml-auto flex items-center gap-1.5"><Megaphone size={14} /> Post</button>
        </div>
      </form>
      {items.map((a) => (
        <div key={a.id} className="flex items-center justify-between text-[13.5px] py-1.5 border-t border-[#3B0A2E]/8">
          <span className="truncate text-[#3B0A2E]">{a.pinned ? 'Pinned · ' : ''}{a.title} <span className="text-[#241019]/40">· {fmtDate(a.created_at)}</span></span>
          <button data-testid={`announce-delete-${a.id}`} onClick={async () => { await api.delete(`/admin/members/announcements/${a.id}`); load(); }} className="text-[#241019]/40 hover:text-red-600"><Trash2 size={14} /></button>
        </div>
      ))}
    </>
  );
}

function BylawsUpload({ toast }) {
  const [info, setInfo] = useState({});
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/members/bylaws').then(({ data }) => setInfo(data)), []);
  useEffect(() => { load(); }, [load]);
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file); setBusy(true);
    try { await api.post('/admin/members/bylaws', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); toast({ title: 'Bylaws updated' }); load(); }
    catch (ex) { toast({ title: 'Upload failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <>
      <p data-testid="bylaws-current" className="text-[13.5px] text-[#241019]/70 mb-4">{info.filename ? <>Current: <b>{info.filename}</b> · updated {fmtDate(info.updated_at)}</> : 'No bylaws uploaded yet.'}</p>
      <label className="border-2 border-dashed border-[#3B0A2E]/20 rounded-xl p-5 text-center cursor-pointer hover:border-[#B4247E] transition-colors block">
        {busy ? <Loader2 className="mx-auto animate-spin text-[#B4247E]" /> : <UploadCloud className="mx-auto text-[#B4247E] mb-1" size={24} />}
        <span className="text-[13px] text-[#241019]/70 block">Upload a new version (.docx). Each "ARTICLE …" heading becomes a section.</span>
        <input data-testid="bylaws-upload-input" type="file" accept=".docx" className="hidden" onChange={(e) => upload(e.target.files?.[0])} />
      </label>
    </>
  );
}

export default function AdminMembers() {
  const { toast } = useToast();
  const [d, setD] = useState({ members: [], invites: [] });
  const load = useCallback(() => api.get('/admin/members').then(({ data }) => setD(data)), []);
  useEffect(() => { load(); }, [load]);
  const act = async (uid, action) => {
    try { await api.post(`/admin/members/${uid}/status`, { action }); toast({ title: 'Updated' }); load(); }
    catch (ex) { toast({ title: 'Failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const apps = d.members.filter((m) => m.status === 'applied');
  return (
    <div className="grid lg:grid-cols-2 gap-6" data-testid="admin-members">
      <Box title={`Applications (${apps.length})`} testid="admin-applications"><Applications rows={apps} act={act} /></Box>
      <Box title="Invite members" testid="admin-invites"><Invites invites={d.invites} reload={load} toast={toast} /></Box>
      <Box title="Announcements" testid="admin-announcements"><AnnouncementForm toast={toast} /></Box>
      <Box title={`Members (${d.members.filter((m) => m.status === 'active').length} active)`} testid="admin-roster"><Roster rows={d.members.filter((m) => m.status !== 'applied')} act={act} /></Box>
      <Box title="Bylaws" testid="admin-bylaws"><BylawsUpload toast={toast} /></Box>
    </div>
  );
}
