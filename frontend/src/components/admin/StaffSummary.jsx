import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Switch } from '../ui/switch';
import { CalendarClock, Send, Loader2 } from 'lucide-react';

export function StaffSummary({ toast }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get('/admin/team/summary-settings').then(({ data }) => setSt(data)).catch(() => {}); }, []);
  if (!st) return null;
  const change = async (quiet_weeks) => {
    try { await api.put('/admin/team/summary-settings', { quiet_weeks }); setSt({ ...st, quiet_weeks }); toast({ title: quiet_weeks ? 'Sent every Monday' : 'Quiet weeks skipped' }); }
    catch (e) { toast({ title: 'Could not update', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };
  const test = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/team/summary-test'); toast({ title: data.sent ? 'Summary sent' : 'Could not send', description: `${data.changes} change(s) this week, sent to ${data.sent} owner inbox(es).`, variant: data.sent ? undefined : 'destructive' }); }
    catch (e) { toast({ title: 'Could not send', description: e?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div data-testid="staff-summary-card" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-2 flex items-center gap-2"><CalendarClock size={18} className="text-[#B4247E]" /> Monday staff summary</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">Every Monday at 9am Eastern, the owners get a short email listing the week's staff changes. Sent to {st.recipients.join(', ')}.</p>
      <label className="flex items-center justify-between gap-3 text-[13px] font-semibold text-[#3B0A2E] mb-4">
        Also send on quiet weeks
        <Switch data-testid="staff-summary-quiet-toggle" checked={st.quiet_weeks} onCheckedChange={change} aria-label="Also send on weeks with no changes" />
      </label>
      <button data-testid="staff-summary-test-btn" disabled={busy} onClick={test} className="rounded-full w-full py-2.5 text-[13.5px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center justify-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send this week's summary now
      </button>
    </div>
  );
}
