import React, { useState } from 'react';
import { api } from '../../lib/api';
import { DoorOpen } from 'lucide-react';
import { fmtDate } from './fmt';

export function LeaveRequest({ me, onChange }) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState('');
  const req = me.leave_request;
  if (me.status !== 'active' || me.is_admin && !me.member_since) return null;
  const send = async () => { await api.post('/members/leave-request', { reason }); setOpen(false); onChange(); };
  const cancel = async () => { await api.delete('/members/leave-request'); onChange(); };
  return (
    <div data-testid="leave-card" className="max-w-xl mt-10 pt-6 border-t border-[#3B0A2E]/10">
      <p className="font-semibold text-[#3B0A2E] flex items-center gap-2 mb-1"><DoorOpen size={16} className="text-[#B4247E]" /> Leaving the Club</p>
      {req ? (
        <>
          <p data-testid="leave-status" className="text-[13.5px] text-[#241019]/70">You asked to leave on {fmtDate(req.requested_at)}.{me.ends_at ? ` Your membership ends on ${fmtDate(me.ends_at + 'T12:00:00')}.` : ' The Executive Board will review it in December.'}</p>
          <button data-testid="leave-cancel-btn" onClick={cancel} className="mt-3 text-[13px] font-semibold text-[#B4247E]">I've changed my mind, withdraw my request</button>
        </>
      ) : open ? (
        <div className="space-y-3 mt-2">
          <textarea data-testid="leave-reason" rows={3} value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Would you like to share why? (optional)" className="w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E]" />
          <div className="flex gap-2">
            <button data-testid="leave-submit-btn" onClick={send} className="rounded-full px-5 py-2 text-[13px] font-semibold bg-[#3B0A2E] text-white">Send request</button>
            <button data-testid="leave-cancel-open-btn" onClick={() => setOpen(false)} className="rounded-full px-5 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E]">Cancel</button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-[13px] text-[#241019]/60">Under Section 5.1, voluntary terminations are accepted in December. Your current-year dues remain payable.</p>
          <button data-testid="leave-open-btn" onClick={() => setOpen(true)} className="mt-3 text-[13px] font-semibold text-[#B4247E]">Request to leave at the end of the year</button>
        </>
      )}
    </div>
  );
}
