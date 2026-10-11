import React, { useCallback, useEffect, useState } from 'react';
import { BellRing, Loader2, Smartphone } from 'lucide-react';
import { api } from '../../lib/api';
import { PushHistory } from './PushHistory';

const inputCls = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';
const DEST = [['/members', 'Member portal'], ['/members?tab=news', 'Announcements'], ['/members?tab=prayer', 'Prayer board'], ['/members?tab=votes', 'Votes'], ['/members?tab=photos', 'Photos'], ['/sessions', 'Sessions'], ['/events', 'Events']];

export const AdminPush = ({ toast }) => {
  const [f, setF] = useState({ title: '', body: '', url: '/members' });
  const [st, setSt] = useState({ devices: 0, members: 0 });
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const load = useCallback(() => api.get('/admin/members/push').then(({ data }) => setSt(data)), []);
  useEffect(() => { load(); }, [load]);
  const test = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/members/push/test', f); toast({ title: `Test sent to ${data.sent} of your device${data.devices === 1 ? '' : 's'}` }); setTick((t) => t + 1); }
    catch (ex) { toast({ title: 'Could not send test', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const send = async (e) => {
    e.preventDefault(); setBusy(true);
    try { const { data } = await api.post('/admin/members/push', f); toast({ title: `Alert sent to ${data.sent} device${data.sent === 1 ? '' : 's'}` }); setF({ title: '', body: '', url: '/members' }); load(); setTick((t) => t + 1); }
    catch (ex) { toast({ title: 'Could not send', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <>
    <form onSubmit={send} className="space-y-3" data-testid="admin-push-form">
      <p data-testid="admin-push-stats" className="text-[13.5px] text-[#241019]/70">{st.members} member{st.members === 1 ? '' : 's'} on {st.devices} device{st.devices === 1 ? '' : 's'} have phone alerts on.</p>
      <input data-testid="admin-push-title" placeholder="Alert title" maxLength={80} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inputCls} />
      <textarea data-testid="admin-push-body" rows={3} placeholder="Short message" maxLength={180} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} className={inputCls} />
      <div className="flex flex-wrap items-center gap-3">
        <select data-testid="admin-push-url" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} className={`${inputCls} w-auto`}>{DEST.map(([v, l]) => <option key={v} value={v}>{`Opens: ${l}`}</option>)}</select>
        <button type="button" data-testid="admin-push-test" disabled={busy} onClick={test} className="rounded-full px-5 py-2 font-semibold ml-auto border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5 hover:bg-[#F7EFE9] transition-colors disabled:opacity-60"><Smartphone size={14} /> Send test to my phone</button>
        <button data-testid="admin-push-send" disabled={busy} className="btn-magenta rounded-full px-5 py-2 font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : <BellRing size={14} />} Send alert</button>
      </div>
    </form>
    <PushHistory refresh={tick} />
    </>
  );
};
