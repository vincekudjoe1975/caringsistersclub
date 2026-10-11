import React, { useCallback, useEffect, useState } from 'react';
import { BellRing, Loader2, Smartphone, CalendarClock } from 'lucide-react';
import { api } from '../../lib/api';
import { PushHistory } from './PushHistory';
import { ScheduledAlerts, WeeklySummaryAdmin } from './ScheduledAlerts';
import { BestTimes, useBestTimes, bestLabel } from './BestTimes';

const inputCls = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';
const DEST = [['/members', 'Member portal'], ['/members?tab=week', 'This Week'], ['/members?tab=news', 'Announcements'], ['/members?tab=prayer', 'Prayer board'], ['/members?tab=votes', 'Votes'], ['/members?tab=photos', 'Photos'], ['/sessions', 'Sessions'], ['/events', 'Events']];
const EMPTY = { title: '', body: '', url: '/members', send_at: '', repeat: 'none', days: [], end_date: '' };
const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

export const AdminPush = ({ toast }) => {
  const [f, setF] = useState(EMPTY);
  const [later, setLater] = useState(false);
  const [editId, setEditId] = useState('');
  const [st, setSt] = useState({ devices: 0, members: 0 });
  const [busy, setBusy] = useState(false);
  const [tick, setTick] = useState(0);
  const best = useBestTimes();
  const load = useCallback(() => api.get('/admin/members/push').then(({ data }) => setSt(data)), []);
  useEffect(() => { load(); }, [load]);
  const reset = () => { setF(EMPTY); setLater(false); setEditId(''); load(); setTick((t) => t + 1); };
  const test = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/members/push/test', f); toast({ title: `Test sent to ${data.sent} of your device${data.devices === 1 ? '' : 's'}` }); setTick((t) => t + 1); }
    catch (ex) { toast({ title: 'Could not send test', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const send = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      if (later) {
        if (editId) await api.put(`/admin/members/push/scheduled/${editId}`, f); else await api.post('/admin/members/push/scheduled', f);
        toast({ title: editId ? 'Scheduled alert updated' : 'Alert scheduled' });
      } else {
        const { data } = await api.post('/admin/members/push', f);
        toast({ title: `Alert sent to ${data.sent} device${data.sent === 1 ? '' : 's'}` });
      }
      reset();
    } catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const edit = (r) => { setF({ title: r.title, body: r.body, url: r.url, send_at: r.send_at_local, repeat: r.repeat || 'none', days: r.days || [], end_date: r.end_date || '' }); setLater(true); setEditId(r.id); };
  const toggleDay = (i) => setF({ ...f, days: f.days.includes(i) ? f.days.filter((x) => x !== i) : [...f.days, i] });
  return (
    <>
    <form onSubmit={send} className="space-y-3" data-testid="admin-push-form">
      <p data-testid="admin-push-stats" className="text-[13.5px] text-[#241019]/70">{st.members} member{st.members === 1 ? '' : 's'} on {st.devices} device{st.devices === 1 ? '' : 's'} have phone alerts on.</p>
      {editId && <p data-testid="admin-push-editing" className="text-[13px] font-semibold text-[#B4247E]">Editing a scheduled alert · <button type="button" data-testid="admin-push-edit-cancel" onClick={reset} className="underline">stop editing</button></p>}
      <input data-testid="admin-push-title" placeholder="Alert title" maxLength={80} value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={inputCls} />
      <textarea data-testid="admin-push-body" rows={3} placeholder="Short message" maxLength={180} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} className={inputCls} />
      <label className="flex items-center gap-2.5 text-[14px] text-[#3B0A2E] cursor-pointer">
        <input data-testid="admin-push-later" type="checkbox" checked={later} disabled={!!editId} onChange={(e) => setLater(e.target.checked)} className="accent-[#B4247E] w-5 h-5" />
        <CalendarClock size={14} className="text-[#B4247E]" /> Send later
      </label>
      {later && <input data-testid="admin-push-send-at" type="datetime-local" required value={f.send_at} onChange={(e) => setF({ ...f, send_at: e.target.value })} className={`${inputCls} w-auto`} />}
      {later && <p data-testid="admin-push-best-hint" className="text-[12.5px] text-[#241019]/55 -mt-1">Eastern time.{best?.best?.length ? ` Sisters tap most on ${bestLabel(best.best[0])}.` : ''}</p>}
      {later && (
        <div className="space-y-2" data-testid="admin-push-repeat-box">
          <select data-testid="admin-push-repeat" value={f.repeat} onChange={(e) => setF({ ...f, repeat: e.target.value })} className={`${inputCls} w-auto`}>
            <option value="none">Does not repeat</option><option value="daily">Repeats daily</option><option value="weekly">Repeats weekly</option><option value="monthly">Repeats monthly (same date)</option>
          </select>
          {f.repeat === 'weekly' && (
            <div className="flex flex-wrap gap-1.5">{WD.map((l, i) => (
              <button type="button" key={l} data-testid={`admin-push-day-${i}`} onClick={() => toggleDay(i)} className={`w-11 h-9 rounded-full text-[12.5px] font-semibold transition-colors ${f.days.includes(i) ? 'bg-[#3B0A2E] text-white' : 'bg-white border border-[#3B0A2E]/15 text-[#3B0A2E]'}`}>{l}</button>
            ))}</div>
          )}
          {f.repeat !== 'none' && <label className="flex items-center gap-2 text-[13px] text-[#3B0A2E]">Ends (optional)<input data-testid="admin-push-end-date" type="date" value={f.end_date} onChange={(e) => setF({ ...f, end_date: e.target.value })} className={`${inputCls} w-auto`} /></label>}
        </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <select data-testid="admin-push-url" value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} className={`${inputCls} w-auto`}>{DEST.map(([v, l]) => <option key={v} value={v}>{`Opens: ${l}`}</option>)}</select>
        <button type="button" data-testid="admin-push-test" disabled={busy} onClick={test} className="rounded-full px-5 py-2 font-semibold ml-auto border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5 hover:bg-[#F7EFE9] transition-colors disabled:opacity-60"><Smartphone size={14} /> Send test to my phone</button>
        <button data-testid="admin-push-send" disabled={busy} className="btn-magenta rounded-full px-5 py-2 font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : later ? <CalendarClock size={14} /> : <BellRing size={14} />} {editId ? 'Save changes' : later ? 'Schedule alert' : 'Send alert'}</button>
      </div>
    </form>
    <ScheduledAlerts toast={toast} refresh={tick} onEdit={edit} />
    <WeeklySummaryAdmin toast={toast} />
    <PushHistory refresh={tick} />
    <BestTimes d={best} />
    </>
  );
};
