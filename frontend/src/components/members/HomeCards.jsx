import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../lib/api';
import { CalendarDays, MapPin, Clock, Send, Sparkles } from 'lucide-react';
import { Avatar } from './Avatar';
import { BirthdaysCard } from './BirthdaysCard';
import { Gatherings, Spotlight } from './HomeExtras';
import { BirthdayToday } from './Phase7';

const longDate = (d) => new Date(d + 'T12:00:00').toLocaleDateString(undefined, { weekday: 'long', month: 'long', day: 'numeric' });
const time12 = (t) => (t ? new Date(`2000-01-01T${t}:00`).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : '');

function NextMeeting() {
  const [m, setM] = useState(null);
  const [text, setText] = useState('');
  const [msg, setMsg] = useState('');
  const load = useCallback(() => api.get('/members/next-meeting').then(({ data }) => setM(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!m) return null;
  const items = [...m.agenda.split('\n').filter((l) => l.trim()).map((l) => l.replace(/^[-•*\d.)\s]+/, '')), ...m.approved_items];
  const suggest = async (e) => {
    e.preventDefault();
    try { await api.post(`/members/meetings/${m.id}/suggestions`, { text }); setText(''); setMsg('Thanks! Your suggestion was sent to the Secretary for review.'); load(); }
    catch (ex) { setMsg(ex?.response?.data?.detail || 'Could not send suggestion.'); }
  };
  return (
    <div data-testid="next-meeting-card" className="bg-white rounded-2xl p-6 mb-6 border-l-4 border-[#CBA24B]">
      <p className="eyebrow text-[#B4247E] mb-1">Next meeting</p>
      <h3 data-testid="next-meeting-title" className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{m.title}</h3>
      <div className="flex flex-wrap gap-4 text-[13px] text-[#241019]/70 mt-1 mb-4">
        <span className="flex items-center gap-1.5"><CalendarDays size={14} className="text-[#B4247E]" /> {longDate(m.date)}</span>
        {m.time && <span className="flex items-center gap-1.5"><Clock size={14} className="text-[#B4247E]" /> {time12(m.time)}</span>}
        {m.location && <span className="flex items-center gap-1.5"><MapPin size={14} className="text-[#B4247E]" /> {m.location}</span>}
      </div>
      <ol data-testid="next-meeting-agenda" className="space-y-1.5 mb-4">
        {items.map((it, i) => <li key={i} className="flex gap-3 text-[14px] text-[#241019]/85"><span className="text-[#CBA24B] font-semibold w-5 shrink-0">{i + 1}.</span>{it}</li>)}
      </ol>
      {m.my_suggestions.length > 0 && <p className="text-[12px] text-[#241019]/55 mb-2">Your suggestions: {m.my_suggestions.map((s) => `"${s.text}" (${s.status})`).join(', ')}</p>}
      <form onSubmit={suggest} className="flex gap-2">
        <input data-testid="agenda-suggest-input" value={text} onChange={(e) => setText(e.target.value)} placeholder="Suggest an agenda item…" className="flex-1 rounded-full border border-[#3B0A2E]/15 px-4 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]" />
        <button data-testid="agenda-suggest-btn" disabled={!text.trim()} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1 disabled:opacity-50"><Send size={13} /> Suggest</button>
      </form>
      {msg && <p data-testid="agenda-suggest-msg" className="text-[12.5px] text-[#241019]/65 mt-2">{msg}</p>}
    </div>
  );
}

function Anniversaries() {
  const [rows, setRows] = useState([]);
  useEffect(() => { api.get('/members/anniversaries').then(({ data }) => setRows(data)).catch(() => {}); }, []);
  if (!rows.length) return null;
  return (
    <div data-testid="anniversaries-card" className="rounded-2xl p-6 mb-6 bg-white border border-[#CBA24B]/40">
      <p className="eyebrow text-[#CBA24B] mb-1 flex items-center gap-2"><Sparkles size={14} /> Sisterhood anniversaries</p>
      <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-4">Thank you for your years of love</h3>
      <div className="grid sm:grid-cols-2 gap-3">
        {rows.map((r) => (
          <div key={r.user_id} data-testid={`anniversary-${r.user_id}`} className={`rounded-xl p-3 flex items-center gap-3 ${r.today ? 'bg-[#faf2f7] ring-2 ring-[#B4247E]/40' : 'bg-[#F7EFE9]'}`}>
            <Avatar name={r.name} src={r.picture} size={38} />
            <div className="min-w-0"><p className="font-semibold text-[#3B0A2E] text-[14px] truncate">{r.name}</p>
              <p className="text-[12.5px] text-[#B4247E] font-semibold">Celebrating {r.years} year{r.years === 1 ? '' : 's'}{r.today ? ' today!' : ` · ${new Date(2000, new Date().getMonth(), r.day).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}`}</p></div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function HomeCards({ me }) {
  return (<><BirthdayToday me={me} /><Spotlight me={me} /><Gatherings /><NextMeeting /><Anniversaries /><BirthdaysCard me={me} /></>);
}
