import React, { useCallback, useEffect, useState } from 'react';
import { Download, Check, X } from 'lucide-react';
import { api } from '../../lib/api';

export const AdminMemberHours = ({ toast }) => {
  const [d, setD] = useState(null);
  const load = useCallback(() => api.get('/admin/members/hours').then(({ data }) => setD(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const review = async (id, action) => {
    try { await api.post(`/admin/volunteer-hours/${id}/${action}`); toast({ title: action === 'approve' ? 'Hours approved' : 'Hours rejected' }); load(); }
    catch (ex) { toast({ title: 'Could not update', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const csv = async () => {
    try {
      const res = await api.get('/admin/members/hours.csv', { responseType: 'blob' });
      const url = URL.createObjectURL(res.data); const a = document.createElement('a');
      a.href = url; a.download = `member-volunteer-hours-${new Date().toISOString().slice(0, 10)}.csv`; a.click(); URL.revokeObjectURL(url);
    } catch { toast({ title: 'Export failed', variant: 'destructive' }); }
  };
  if (!d) return null;
  return (
    <div data-testid="admin-member-hours" className="space-y-5 text-[13.5px]">
      <div className="flex items-center justify-between gap-3">
        <p className="text-[#241019]/70">{d.pending.length} entr{d.pending.length === 1 ? 'y' : 'ies'} waiting for approval</p>
        <button data-testid="admin-hours-csv" onClick={csv} className="rounded-full px-4 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5 hover:bg-[#F7EFE9] transition-colors"><Download size={14} /> CSV</button>
      </div>
      {d.pending.map((h) => (
        <div key={h.id} data-testid={`admin-hours-pending-${h.id}`} className="flex items-start gap-3 py-2 border-t border-[#3B0A2E]/8">
          <div className="min-w-0 flex-1"><p className="font-semibold text-[#3B0A2E]">{h.name} · {h.hours}h</p><p className="text-[#241019]/60 break-words">{h.date} · {h.activity || h.program}{h.note ? ` · ${h.note}` : ''}</p></div>
          <button data-testid={`admin-hours-approve-${h.id}`} onClick={() => review(h.id, 'approve')} aria-label="Approve" className="w-9 h-9 rounded-full bg-emerald-50 text-emerald-700 flex items-center justify-center hover:bg-emerald-100"><Check size={15} /></button>
          <button data-testid={`admin-hours-reject-${h.id}`} onClick={() => review(h.id, 'reject')} aria-label="Reject" className="w-9 h-9 rounded-full bg-red-50 text-red-600 flex items-center justify-center hover:bg-red-100"><X size={15} /></button>
        </div>
      ))}
      <div>
        <p className="font-semibold text-[#3B0A2E] mb-2">Leaderboard</p>
        {!d.leaderboard.length ? <p className="text-[#241019]/55">No member hours logged yet.</p> : (
          <ol data-testid="admin-hours-leaderboard" className="space-y-1.5">
            {d.leaderboard.map((b, i) => (
              <li key={b.email} data-testid={`admin-hours-row-${b.user_id}`} className="flex items-center gap-3">
                <span className="w-6 text-[#241019]/45 font-semibold">{i + 1}</span>
                <span className="flex-1 min-w-0 truncate text-[#3B0A2E] font-medium">{b.name}</span>
                {b.badge > 0 && <span className="rounded-full px-2 py-0.5 text-[11.5px] font-semibold bg-[#3B0A2E] text-[#CBA24B]">{b.badge}h badge</span>}
                <span className="font-semibold text-[#B4247E] w-16 text-right">{b.approved}h</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </div>
  );
};
