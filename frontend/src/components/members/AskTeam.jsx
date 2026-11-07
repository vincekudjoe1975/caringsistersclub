import React, { useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { MessageCircleQuestion, Loader2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../ui/dialog';

export function AskTeam({ m }) {
  const { toast } = useToast();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState('');
  const [busy, setBusy] = useState(false);
  const first = (m.name || 'her').split(' ')[0];
  const send = async () => {
    setBusy(true);
    try {
      await api.post('/members/team-questions', { to_user_id: m.user_id, text });
      toast({ title: 'Question sent', description: `${first} will get it by email. Her answer will show in My Profile → Questions.` });
      setText(''); setOpen(false);
    } catch (e) { toast({ title: 'Could not send', description: e?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <>
      <button data-testid={`directory-ask-${m.user_id}`} onClick={() => setOpen(true)} className="mt-3 rounded-full px-3.5 py-1.5 text-[12.5px] font-semibold border border-[#B4247E]/40 text-[#B4247E] hover:bg-[#B4247E] hover:text-white flex items-center gap-1.5 transition-colors">
        <MessageCircleQuestion size={14} /> Ask {first} a question
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent data-testid="ask-team-dialog">
          <DialogHeader>
            <DialogTitle>Ask {first}</DialogTitle>
            <DialogDescription>{first} is on the Club team. She'll get your question by email and can answer you here or by email.</DialogDescription>
          </DialogHeader>
          <textarea data-testid="ask-team-text" rows={5} value={text} onChange={(e) => setText(e.target.value)} maxLength={1500} placeholder="Type your question…"
            className="w-full rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
          <button data-testid="ask-team-send" disabled={busy || text.trim().length < 3} onClick={send} className="btn-magenta rounded-full py-3 font-semibold flex items-center justify-center gap-2 disabled:opacity-50">
            {busy && <Loader2 size={15} className="animate-spin" />} Send question
          </button>
        </DialogContent>
      </Dialog>
    </>
  );
}
