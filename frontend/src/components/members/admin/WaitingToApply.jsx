import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { Hourglass, Loader2 } from 'lucide-react';

const d = (iso) => (iso ? new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }) : '');

export function WaitingToApply({ toast }) {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/members/waiting').then(({ data }) => setS(data)).catch(() => setS({ enabled: true, rows: [] })), []);
  useEffect(() => { load(); }, [load]);
  const toggle = async () => {
    setBusy(true);
    try { const { data } = await api.put('/admin/members/apply-reminders', { enabled: !s.enabled }); setS((x) => ({ ...x, enabled: data.enabled })); toast({ title: data.enabled ? 'Reminders on' : 'Reminders paused' }); }
    catch (ex) { toast({ title: 'Could not update', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  if (!s) return <Loader2 className="animate-spin text-[#B4247E]" size={18} />;
  return (
    <div data-testid="waiting-to-apply">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
        <p className="text-[13px] text-[#241019]/65 max-w-md">Sisters who created an account but haven't sent their application. They get a friendly reminder after 3 days and a final one after 7 days.</p>
        <label className="flex items-center gap-2 text-[13px] font-semibold text-[#3B0A2E] cursor-pointer">
          <input data-testid="apply-reminders-toggle" type="checkbox" checked={s.enabled} disabled={busy} onChange={toggle} className="accent-[#B4247E] w-5 h-5" />
          Send reminders
        </label>
      </div>
      {!s.rows.length ? <p data-testid="waiting-empty" className="text-[13.5px] text-[#241019]/50">No one is waiting to apply.</p> : (
        <ul className="divide-y divide-[#3B0A2E]/8">
          {s.rows.map((r) => (
            <li key={r.user_id} data-testid={`waiting-row-${r.user_id}`} className="py-2.5 flex flex-wrap items-start justify-between gap-2">
              <div className="min-w-0"><p className="text-[14px] font-semibold text-[#3B0A2E] truncate">{r.name || r.email}</p><p className="text-[12px] text-[#241019]/55 break-all">{r.email} · {r.signed_up_with} · joined {d(r.confirmed_at)}</p></div>
              <p data-testid={`waiting-reminders-${r.user_id}`} className="text-[12px] text-[#241019]/60 flex items-center gap-1.5"><Hourglass size={12} className="text-[#B4247E]" />
                {r.reminder_2_at ? `Reminded ${d(r.reminder_1_at)} and ${d(r.reminder_2_at)} (done)` : r.reminder_1_at ? `Reminded ${d(r.reminder_1_at)} · final at 7 days` : r.eligible ? 'First reminder at 3 days' : 'Joined before reminders started'}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
