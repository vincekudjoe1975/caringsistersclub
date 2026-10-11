import React, { useCallback, useEffect, useState } from 'react';
import { CalendarClock, Pencil, X, Loader2, Pause, Play, Repeat } from 'lucide-react';
import { api } from '../../lib/api';

const WD = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const repeatLabel = (r) => (r.repeat === 'daily' ? 'Daily' : r.repeat === 'weekly' ? `Weekly on ${r.days.map((d) => WD[d]).join(', ')}` : r.repeat === 'monthly' ? 'Monthly' : '');

export const ScheduledAlerts = ({ toast, refresh, onEdit }) => {
  const [rows, setRows] = useState([]);
  const load = useCallback(() => api.get('/admin/members/push/scheduled').then(({ data }) => setRows(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load, refresh]);
  const cancel = async (id) => {
    try { await api.delete(`/admin/members/push/scheduled/${id}`); toast({ title: 'Scheduled alert cancelled' }); load(); }
    catch (ex) { toast({ title: 'Could not cancel', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const pause = async (id, action) => {
    try { await api.post(`/admin/members/push/scheduled/${id}/${action}`); toast({ title: action === 'pause' ? 'Alert paused' : 'Alert resumed' }); load(); }
    catch (ex) { toast({ title: 'Could not update', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  if (!rows.length) return null;
  return (
    <div data-testid="scheduled-alerts" className="mt-5 pt-4 border-t border-[#3B0A2E]/10">
      <p className="font-semibold text-[#3B0A2E] mb-2 flex items-center gap-1.5"><CalendarClock size={15} className="text-[#B4247E]" /> Scheduled alerts</p>
      {rows.map((r) => (
        <div key={r.id} data-testid={`scheduled-row-${r.id}`} className="py-2.5 border-t border-[#3B0A2E]/8 flex items-start gap-3 text-[13px]">
          <div className="min-w-0 flex-1">
            <p className="font-semibold text-[#3B0A2E] break-words">{r.title}</p>
            <p className="text-[#241019]/55">{r.status === 'paused' ? <span data-testid={`scheduled-paused-${r.id}`} className="font-semibold text-amber-700">Paused · </span> : 'Next: '}{new Date(r.send_at).toLocaleString(undefined, { timeZone: 'America/New_York', weekday: 'short', month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })} Eastern</p>
            {r.repeat && r.repeat !== 'none' && <p data-testid={`scheduled-repeat-${r.id}`} className="text-[#B4247E] font-semibold flex items-center gap-1"><Repeat size={12} /> {repeatLabel(r)}{r.end_date ? ` until ${r.end_date}` : ''}{r.sent_count ? ` · sent ${r.sent_count}×` : ''}</p>}
          </div>
          <button type="button" data-testid={`scheduled-${r.status === 'paused' ? 'resume' : 'pause'}-${r.id}`} onClick={() => pause(r.id, r.status === 'paused' ? 'resume' : 'pause')} aria-label={r.status === 'paused' ? 'Resume' : 'Pause'} className="w-9 h-9 flex items-center justify-center rounded-full text-[#3B0A2E]/70 hover:bg-[#F7EFE9]">{r.status === 'paused' ? <Play size={14} /> : <Pause size={14} />}</button>
          <button type="button" data-testid={`scheduled-edit-${r.id}`} onClick={() => onEdit(r)} aria-label="Edit" className="w-9 h-9 flex items-center justify-center rounded-full text-[#3B0A2E]/70 hover:bg-[#F7EFE9]"><Pencil size={14} /></button>
          <button type="button" data-testid={`scheduled-cancel-${r.id}`} onClick={() => cancel(r.id)} aria-label="Cancel" className="w-9 h-9 flex items-center justify-center rounded-full text-red-600/80 hover:bg-red-50"><X size={15} /></button>
        </div>
      ))}
    </div>
  );
};

export const WeeklySummaryAdmin = ({ toast }) => {
  const [c, setC] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/members/weekly-summary').then(({ data }) => setC(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!c) return null;
  const toggle = async () => { await api.put('/admin/members/weekly-summary', { paused: !c.paused }); toast({ title: c.paused ? 'Weekly summary resumed' : 'Weekly summary paused' }); load(); };
  const sendNow = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/members/weekly-summary/send'); toast({ title: `Weekly summary sent to ${data.sent} device${data.sent === 1 ? '' : 's'}` }); load(); }
    catch (ex) { toast({ title: 'Could not send', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="weekly-summary-admin" className="mt-5 pt-4 border-t border-[#3B0A2E]/10 text-[13.5px]">
      <p className="font-semibold text-[#3B0A2E]">Weekly summary alert <span className="font-normal text-[#241019]/55">· Sundays 6pm Eastern</span></p>
      <p data-testid="weekly-summary-status" className="text-[#241019]/65 mt-1">{c.paused ? 'Paused' : 'On'}{c.last_sent ? ` · last sent ${new Date(c.last_sent).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}` : ''}</p>
      <p data-testid="weekly-summary-preview" className="mt-2 rounded-xl bg-[#F7EFE9] px-3 py-2 text-[#3B0A2E]">"{c.preview}"</p>
      <div className="flex flex-wrap gap-2 mt-3">
        <button type="button" data-testid="weekly-summary-toggle" onClick={toggle} className="rounded-full px-4 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] hover:bg-[#F7EFE9] transition-colors">{c.paused ? 'Resume' : 'Pause'}</button>
        <button type="button" data-testid="weekly-summary-send" disabled={busy} onClick={sendNow} className="btn-magenta rounded-full px-4 py-2 font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy && <Loader2 size={13} className="animate-spin" />} Send now</button>
      </div>
    </div>
  );
};
