import React, { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';

export function RemindButton({ r, onSend }) {
  const [open, setOpen] = useState(false);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const go = async () => { setBusy(true); if (await onSend(r, note)) { setOpen(false); setNote(''); } setBusy(false); };
  if (!open) {
    return <button data-testid={`waiting-remind-btn-${r.user_id}`} onClick={() => setOpen(true)} className="rounded-full px-3 py-1 text-[12px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] flex items-center gap-1 transition-colors"><Send size={12} /> Send reminder</button>;
  }
  return (
    <div data-testid={`waiting-remind-form-${r.user_id}`} className="w-full mt-2 space-y-2">
      <textarea data-testid={`waiting-remind-note-${r.user_id}`} rows={2} maxLength={500} value={note} onChange={(e) => setNote(e.target.value)}
        placeholder={`Optional personal note, e.g. "Hi ${(r.name || '').split(' ')[0] || 'there'}, we'd love to see you at our next gathering!"`}
        className="w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13px] focus:outline-none focus:border-[#B4247E]" />
      <div className="flex gap-2">
        <button data-testid={`waiting-remind-send-${r.user_id}`} disabled={busy} onClick={go} className="btn-magenta rounded-full px-4 py-1.5 text-[12.5px] font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={12} className="animate-spin" /> : <Send size={12} />} Send reminder</button>
        <button data-testid={`waiting-remind-cancel-${r.user_id}`} onClick={() => setOpen(false)} className="rounded-full px-3 py-1.5 text-[12.5px] font-semibold text-[#241019]/60">Cancel</button>
      </div>
    </div>
  );
}
