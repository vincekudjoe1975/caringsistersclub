import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { Cake, Send, Loader2 } from 'lucide-react';
import { Avatar } from './Avatar';

const MONTH = new Date().toLocaleString(undefined, { month: 'long' });

function Wish({ b, me, onSent }) {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState(`Happy birthday, ${b.name.split(' ')[0]}! Wishing you a beautiful year ahead.`);
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    try { await api.post(`/members/birthdays/${b.user_id}/wish`, { message: msg }); setOpen(false); onSent(b.name); } finally { setBusy(false); }
  };
  if (b.user_id === me.user_id) return <span className="text-[12px] text-[#CBA24B] font-semibold">That's you!</span>;
  if (!open) return <button data-testid={`wish-btn-${b.user_id}`} onClick={() => setOpen(true)} className="text-[12.5px] font-semibold text-[#B4247E] hover:underline">Send wishes</button>;
  return (
    <div className="w-full mt-2 flex gap-2">
      <input data-testid={`wish-input-${b.user_id}`} value={msg} onChange={(e) => setMsg(e.target.value)} className="flex-1 rounded-full border border-[#3B0A2E]/15 px-3 py-1.5 text-[13px] bg-white focus:outline-none focus:border-[#B4247E]" />
      <button data-testid={`wish-send-${b.user_id}`} onClick={send} disabled={busy} className="btn-magenta rounded-full px-3 py-1.5 text-[12.5px] font-semibold flex items-center gap-1">{busy ? <Loader2 className="animate-spin" size={13} /> : <Send size={13} />} Post</button>
    </div>
  );
}

export function BirthdaysCard({ me }) {
  const [rows, setRows] = useState([]);
  const [sent, setSent] = useState('');
  useEffect(() => { api.get('/members/birthdays').then(({ data }) => setRows(data)).catch(() => {}); }, []);
  if (!rows.length) return null;
  return (
    <div data-testid="birthdays-card" className="rounded-2xl p-6 mb-6 relative overflow-hidden" style={{ background: 'linear-gradient(135deg,#3B0A2E,#7a1a5c)' }}>
      <div className="absolute -right-10 -top-10 w-40 h-40 rounded-full opacity-25" style={{ background: 'radial-gradient(circle,#CBA24B,transparent 70%)' }} />
      <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><Cake size={14} /> {MONTH} birthdays</p>
      <h3 className="font-serif text-[22px] text-[#F7EFE9] font-semibold mb-4">Celebrate your sisters this month</h3>
      <div className="grid sm:grid-cols-2 gap-3 relative">
        {rows.map((b) => (
          <div key={b.user_id} data-testid={`birthday-${b.user_id}`} className="bg-white/95 rounded-xl p-3 flex flex-wrap items-center gap-3">
            <Avatar name={b.name} src={b.picture} size={38} />
            <div className="flex-1 min-w-0"><p className="font-semibold text-[#3B0A2E] text-[14px] truncate">{b.name}</p><p className="text-[12px] text-[#241019]/55">{MONTH} {b.day}</p></div>
            <Wish b={b} me={me} onSent={(n) => setSent(n)} />
            <a data-testid={`wall-link-${b.user_id}`} href={`/birthday-wishes/${b.user_id}`} className="text-[12px] text-[#3B0A2E]/60 hover:text-[#B4247E] font-semibold">View wishes</a>
          </div>
        ))}
      </div>
      {sent && <p data-testid="wish-sent" className="text-[13px] text-[#F7EFE9]/85 mt-3">Your wishes for {sent} were posted in Discussion.</p>}
    </div>
  );
}
