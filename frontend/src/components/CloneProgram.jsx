import React, { useState } from 'react';
import { Loader2, Copy, X } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const OPTIONS = [
  ['claim', 'Offer seats to the waitlist first', 'On publish, waitlisted sisters get 48-hour claim links before public sign-ups open.'],
  ['auto', 'Move the waitlist in automatically', 'On publish, waitlisted sisters fill the seats right away and get a "You\'re in!" email.'],
  ['none', 'Just copy the program', 'No waitlist transfer.'],
];

export const CloneProgramDialog = ({ program, onClose, onDone }) => {
  const { toast } = useToast();
  const [capacity, setCapacity] = useState(program.capacity || 10);
  const [transfer, setTransfer] = useState('claim');
  const [busy, setBusy] = useState(false);
  const submit = async () => {
    setBusy(true);
    try {
      const { data } = await api.post(`/admin/programs/${program.id}/clone`, { capacity: Number(capacity) || 0, transfer });
      toast({ title: `Created "${data.title}"`, description: `Saved hidden. Publish it in Programs${transfer !== 'none' && data.source_waitlist ? ` to bring over ${Math.min(data.source_waitlist, data.capacity || data.source_waitlist)} waitlisted sister(s)` : ''}.` });
      onDone?.(data);
      onClose();
    } catch (err) { toast({ title: 'Clone failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl max-w-lg w-full p-7" data-testid="clone-program-dialog">
        <div className="flex items-start justify-between mb-1">
          <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Clone as new session</h3>
          <button onClick={onClose} className="p-1 text-[#3B0A2E]" data-testid="clone-close-btn"><X size={18} /></button>
        </div>
        <p className="text-[13px] text-[#241019]/60 mb-5">Copies <strong>{program.title}</strong> as a new hidden session you can review before publishing.</p>
        <label className="text-[13px] font-semibold text-[#3B0A2E]">Seats in the new session (0 = unlimited)</label>
        <input type="number" min="0" value={capacity} onChange={(e) => setCapacity(e.target.value)} data-testid="clone-capacity-input" className="w-full mt-1.5 mb-5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px]" />
        <p className="text-[13px] font-semibold text-[#3B0A2E] mb-2">Waitlist from the current session</p>
        <div className="space-y-2 mb-6">
          {OPTIONS.map(([v, t, d]) => (
            <label key={v} className={`flex gap-3 p-3 rounded-xl border cursor-pointer ${transfer === v ? 'border-[#B4247E] bg-[#faf2f7]' : 'border-[#3B0A2E]/10'}`}>
              <input type="radio" name="transfer" checked={transfer === v} onChange={() => setTransfer(v)} data-testid={`clone-transfer-${v}`} className="accent-[#B4247E] mt-1" />
              <span><span className="block text-[13.5px] font-semibold text-[#3B0A2E]">{t}</span><span className="block text-[12px] text-[#241019]/60">{d}</span></span>
            </label>
          ))}
        </div>
        <button onClick={submit} disabled={busy} data-testid="clone-submit-btn" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px] flex items-center gap-2 disabled:opacity-60">{busy ? <Loader2 size={15} className="animate-spin" /> : <Copy size={15} />} Create session</button>
      </div>
    </div>
  );
};
