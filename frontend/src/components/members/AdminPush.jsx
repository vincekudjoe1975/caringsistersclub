import React, { useCallback, useEffect, useState } from 'react';
import { BellRing, Loader2 } from 'lucide-react';
import { api } from '../../lib/api';

const inputCls = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';
const DEST = [['/members', 'Member portal'], ['/members?tab=news', 'Announcements'], ['/members?tab=prayer', 'Prayer board'], ['/members?tab=votes', 'Votes'], ['/members?tab=photos', 'Photos'], ['/sessions', 'Sessions'], ['/events', 'Events']];

export const AdminPush = ({ toast }) => {
  const [f, setF] = useState({ title: '', body: '', url: '/members' });
  const [st, setSt] = useState({ devices: 0, members: 0 });
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/members/push').then(({ data }) => setSt(data)), []);
  useEffect(() => { load(); }, [load]);
  const send = async (e) => {
    e.preventDefault(); setBusy(true);
    try { const { data } = await api.post('/admin/members/push', f); toast({ title: `Alert sent to ${data.sent} device${data.sent === 1 ? '' : 's'}` }); setF({ title: '', body: '', url: '/members' }); load(); }
    catch (ex) { toast({ title: 'Could not send', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={send} className="space-y-3" data-testid="admin-push-form">
      <p data-testid="admin-push-stats" className="text-[13.5px] text-[#241019]/70">{st.members} member{st.members === 1 ? '' : 's'} on {st.devices} device{st.devices === 1 ? '' : 's'} have phone alerts on.</p>
      <input data-testid="admin-push-title" placeholder="Alert title" maxLength={80} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inputCls} />
      <textarea data-testid="admin-push-body" rows={3} placeholder="Short message" maxLength={180} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} className={inputCls} />
      <div className="flex flex-wrap items-center gap-3">
        <select data-testid="admin-push-url" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} className={`${inputCls} w-auto`}>{DEST.map(([v, l]) => <option key={v} value={v}>Opens: {l}</option>)}</select>
        <button data-testid="admin-push-send" disabled={busy} className="btn-magenta rounded-full px-5 py-2 font-semibold ml-auto flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : <BellRing size={14} />} Send alert</button>
      </div>
    </form>
  );
};
