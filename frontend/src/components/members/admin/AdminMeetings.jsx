import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Plus, Trash2, AlertTriangle, Save, FileText, ListChecks, PartyPopper } from 'lucide-react';
import { fmtDate } from '../fmt';

const FLAG = { warning: 'Warning letter (2 in a row)', fine: '$10 fine (3 in a row)', officer_removal: 'Officer: 3 missed, remove from office', termination: '4+ missed: ends in December' };
const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const STATES = ['present', 'absent', 'excused'];
const BTN = { present: 'bg-green-600 text-white', absent: 'bg-red-600 text-white', excused: 'bg-[#241019]/50 text-white' };

function AttendanceSheet({ m, members, onSaved }) {
  const { toast } = useToast();
  const [att, setAtt] = useState(m.attendance || {});
  const save = async () => { await api.put(`/admin/members/meetings/${m.id}/attendance`, { attendance: att }); toast({ title: 'Attendance saved', description: 'Warnings and fines were updated automatically.' }); onSaved(); };
  return (
    <div data-testid={`sheet-${m.id}`} className="bg-[#faf2f7] rounded-xl p-4 mt-3">
      <div className="flex gap-2 mb-3">
        <button data-testid={`all-present-${m.id}`} onClick={() => setAtt(Object.fromEntries(members.map((x) => [x.user_id, 'present'])))} className="text-[12.5px] font-semibold text-[#B4247E]">Mark everyone present</button>
      </div>
      {members.map((x) => (
        <div key={x.user_id} className="flex items-center justify-between py-1.5 text-[13.5px]">
          <span>{x.name}{x.office && <span className="text-[11px] text-[#B4247E] ml-1.5">{x.office}</span>}</span>
          <span className="flex gap-1">
            {STATES.map((s) => <button key={s} data-testid={`att-${m.id}-${x.user_id}-${s}`} onClick={() => setAtt({ ...att, [x.user_id]: s })} className={`rounded-full px-3 py-1 text-[12px] font-semibold capitalize transition-colors ${att[x.user_id] === s ? BTN[s] : 'bg-white text-[#241019]/60 border border-[#3B0A2E]/10'}`}>{s}</button>)}
          </span>
        </div>
      ))}
      <button data-testid={`att-save-${m.id}`} onClick={save} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold mt-3 flex items-center gap-1.5"><Save size={14} /> Save attendance</button>
    </div>
  );
}

function MinutesEditor({ m, onSaved }) {
  const { toast } = useToast();
  const [body, setBody] = useState(m.minutes?.body || '');
  const save = async (approve) => {
    try { await api.put(`/admin/members/meetings/${m.id}/minutes`, { body, approve }); toast({ title: approve ? 'Minutes approved and shared with members' : 'Draft saved' }); onSaved(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div data-testid={`minutes-editor-${m.id}`} className="bg-[#faf2f7] rounded-xl p-4 mt-3">
      <textarea data-testid={`minutes-body-${m.id}`} rows={8} value={body} onChange={(e) => setBody(e.target.value)} placeholder="Call to order, attendance, reports, motions, votes (yeas/nays/abstentions), adjournment…" className={`${inputCls} w-full`} />
      <div className="flex gap-2 mt-2">
        <button data-testid={`minutes-draft-${m.id}`} onClick={() => save(false)} className="rounded-full px-4 py-2 text-[12.5px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] bg-white">Save draft</button>
        <button data-testid={`minutes-approve-${m.id}`} onClick={() => save(true)} className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold">Approve & share with members</button>
      </div>
    </div>
  );
}

function AgendaEditor({ m, onSaved }) {
  const { toast } = useToast();
  const [f, setF] = useState({ body: m.agenda?.body || '', time: m.time || '', location: m.location || '' });
  const published = m.agenda?.status === 'published';
  const save = async (publish) => {
    try { await api.put(`/admin/members/meetings/${m.id}/agenda`, { ...f, publish }); toast({ title: publish ? 'Agenda published' : 'Agenda saved', description: publish ? 'Members see it as the next meeting; a reminder email goes out the day before.' : undefined }); onSaved(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const decide = async (sid, action) => { await api.post(`/admin/members/meetings/${m.id}/suggestions/${sid}`, { action }); onSaved(); };
  const pending = (m.suggestions || []).filter((s) => s.status === 'pending');
  return (
    <div data-testid={`agenda-editor-${m.id}`} className="bg-[#faf2f7] rounded-xl p-4 mt-3 space-y-2">
      <div className="flex gap-2">
        <input data-testid={`agenda-time-${m.id}`} type="time" value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} className={inputCls} />
        <input data-testid={`agenda-location-${m.id}`} placeholder="Location or video link" value={f.location} onChange={(e) => setF({ ...f, location: e.target.value })} className={`${inputCls} flex-1`} />
      </div>
      <textarea data-testid={`agenda-body-${m.id}`} rows={6} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} placeholder={'One item per line, e.g.\nOpening prayer\nTreasurer\'s report\nOld business'} className={`${inputCls} w-full`} />
      <div className="flex flex-wrap gap-2 items-center">
        <button data-testid={`agenda-draft-${m.id}`} onClick={() => save(false)} className="rounded-full px-4 py-2 text-[12.5px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] bg-white">{published ? 'Save changes' : 'Save draft'}</button>
        {!published && <button data-testid={`agenda-publish-${m.id}`} onClick={() => save(true)} className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold">Publish to members</button>}
        {published && <button data-testid={`agenda-unpublish-${m.id}`} onClick={async () => { await api.post(`/admin/members/meetings/${m.id}/agenda/unpublish`); onSaved(); }} className="text-[12.5px] font-semibold text-[#241019]/55">Unpublish</button>}
        {m.agenda?.reminder_sent_at && <span className="text-[12px] text-green-700">Reminder emailed {fmtDate(m.agenda.reminder_sent_at)}</span>}
      </div>
      {(m.suggestions || []).length > 0 && (
        <div className="pt-2">
          <p className="text-[12px] font-semibold text-[#3B0A2E] mb-1">Member suggestions ({pending.length} pending)</p>
          {m.suggestions.map((s) => (
            <div key={s.id} className="flex items-center justify-between gap-2 text-[13px] py-1">
              <span className="min-w-0"><b>{s.author_name}:</b> {s.text}</span>
              {s.status === 'pending' ? <span className="flex gap-2 shrink-0">
                <button data-testid={`sug-approve-${s.id}`} onClick={() => decide(s.id, 'approve')} className="text-[12px] font-semibold text-green-700">Add to agenda</button>
                <button data-testid={`sug-decline-${s.id}`} onClick={() => decide(s.id, 'decline')} className="text-[12px] font-semibold text-[#241019]/50">Decline</button>
              </span> : <span className={`text-[12px] shrink-0 ${s.status === 'approved' ? 'text-green-700' : 'text-[#241019]/45'}`}>{s.status}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function GatheringPanel({ m, onSaved }) {
  const [d, setD] = useState(null);
  const [f, setF] = useState({ rsvp_deadline: m.rsvp_deadline || '', details: m.details || '' });
  const load = useCallback(() => api.get(`/admin/members/meetings/${m.id}/rsvps`).then(({ data }) => setD(data)), [m.id]);
  useEffect(() => { load(); }, [load]);
  const save = async () => { await api.put(`/admin/members/meetings/${m.id}/gathering`, f); onSaved(); load(); };
  if (!d) return null;
  const h = d.headcount;
  return (
    <div data-testid={`gathering-panel-${m.id}`} className="bg-[#faf2f7] rounded-xl p-4 mt-3 space-y-3">
      <div className="grid grid-cols-4 gap-2 text-center">
        {[['Coming', h.total, 'hc-total'], ['Members yes', h.yes, 'hc-yes'], ['Maybe', h.maybe_total, 'hc-maybe'], ['No', h.no, 'hc-no']].map(([l, v, t]) => (
          <div key={l} className="bg-white rounded-lg py-2"><p className="text-[11px] text-[#241019]/55">{l}</p><p data-testid={`${t}-${m.id}`} className="font-semibold text-[#3B0A2E] text-[18px]">{v}</p></div>
        ))}
      </div>
      <p className="text-[12px] text-[#241019]/60">Includes {h.guests} guest{h.guests === 1 ? '' : 's'}. A reminder goes to sisters without an RSVP 7 days before{d.reminder_sent_at ? ` (sent ${fmtDate(d.reminder_sent_at)})` : ''}.</p>
      <div className="flex flex-wrap gap-2">
        <label className="text-[12px] text-[#241019]/60">RSVP deadline<input data-testid={`gathering-deadline-${m.id}`} type="date" value={f.rsvp_deadline} onChange={(e) => setF({ ...f, rsvp_deadline: e.target.value })} className={`${inputCls} block`} /></label>
        <textarea data-testid={`gathering-details-${m.id}`} rows={2} value={f.details} onChange={(e) => setF({ ...f, details: e.target.value })} placeholder="Details for sisters (menu, dress code, what to bring…)" className={`${inputCls} flex-1 min-w-[200px]`} />
        <button data-testid={`gathering-save-${m.id}`} onClick={save} className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold self-end">Save</button>
      </div>
      {d.dietary.length > 0 && <div><p className="text-[12px] font-semibold text-[#3B0A2E]">Dietary notes</p>{d.dietary.map((x, i) => <p key={i} className="text-[12.5px] text-[#241019]/75">{x.name}: {x.note}</p>)}</div>}
      <div className="grid md:grid-cols-2 gap-3 text-[12.5px]">
        <div><p className="font-semibold text-[#3B0A2E] mb-1">Replies</p>{d.rows.map((r) => <p key={r.user_id}>{r.name}: <b className={r.response === 'yes' ? 'text-green-700' : r.response === 'no' ? 'text-red-600' : 'text-amber-700'}>{r.response}</b>{r.guests ? ` +${r.guests}` : ''}</p>)}{!d.rows.length && <p className="text-[#241019]/50">No replies yet.</p>}</div>
        <div><p className="font-semibold text-[#3B0A2E] mb-1">No reply yet ({d.no_reply.length})</p><p data-testid={`no-reply-${m.id}`} className="text-[#241019]/65">{d.no_reply.join(', ') || 'Everyone has replied'}</p></div>
      </div>
    </div>
  );
}

export function AdminMeetings() {
  const [d, setD] = useState(null);
  const [f, setF] = useState({ title: 'General meeting', date: '', kind: 'general' });
  const [open, setOpen] = useState(null);
  const [mins, setMins] = useState(null);
  const [agenda, setAgenda] = useState(null);
  const [rsvp, setRsvp] = useState(null);
  const load = useCallback(() => api.get('/admin/members/meetings').then(({ data }) => setD(data)), []);
  useEffect(() => { load(); }, [load]);
  const create = async (e) => { e.preventDefault(); const { data } = await api.post('/admin/members/meetings', f); setOpen(data.id); load(); };
  if (!d) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6" data-testid="admin-meetings">
      <div>
        <form onSubmit={create} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 flex flex-wrap gap-2 mb-5">
          <input data-testid="meeting-title" value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} className={`${inputCls} flex-1 min-w-[160px]`} />
          <input data-testid="meeting-date" type="date" required value={f.date} onChange={(e) => setF({ ...f, date: e.target.value })} className={inputCls} />
          <select data-testid="meeting-kind" value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })} className={inputCls}><option value="general">General</option><option value="in-person">In-person</option><option value="executive">Executive</option></select>
          <button data-testid="meeting-create-btn" className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1"><Plus size={14} /> Add meeting</button>
        </form>
        <div className="space-y-3">
          {d.meetings.map((m) => (
            <div key={m.id} data-testid={`meeting-${m.id}`} className="bg-white rounded-2xl p-4 border border-[#3B0A2E]/8">
              <div className="flex items-center justify-between gap-3">
                <div><p className="font-semibold text-[#3B0A2E] text-[14.5px]">{m.title}</p><p className="text-[12px] text-[#241019]/50">{fmtDate(m.date + 'T12:00:00')} · {m.kind} · {Object.values(m.attendance || {}).filter((v) => v === 'present').length} present</p></div>
                <span className="flex gap-3 items-center">
                  {m.minutes && <span data-testid={`minutes-status-${m.id}`} className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${m.minutes.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>Minutes {m.minutes.status}</span>}
                  {m.agenda && <span data-testid={`agenda-status-${m.id}`} className={`text-[11px] font-semibold px-2 py-0.5 rounded-full ${m.agenda.status === 'published' ? 'bg-green-100 text-green-800' : 'bg-amber-100 text-amber-800'}`}>Agenda {m.agenda.status}</span>}
                  {m.kind === 'in-person' && <button data-testid={`meeting-rsvps-${m.id}`} onClick={() => setRsvp(rsvp === m.id ? null : m.id)} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><PartyPopper size={13} /> RSVPs</button>}
                  <button data-testid={`meeting-agenda-${m.id}`} onClick={() => setAgenda(agenda === m.id ? null : m.id)} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><ListChecks size={13} /> Agenda</button>
                  <button data-testid={`meeting-minutes-${m.id}`} onClick={() => setMins(mins === m.id ? null : m.id)} className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1"><FileText size={13} /> Minutes</button>
                  <button data-testid={`meeting-open-${m.id}`} onClick={() => setOpen(open === m.id ? null : m.id)} className="text-[12.5px] font-semibold text-[#B4247E]">{open === m.id ? 'Close' : 'Take attendance'}</button>
                  <button data-testid={`meeting-del-${m.id}`} onClick={async () => { if (window.confirm('Delete this meeting and its attendance?')) { await api.delete(`/admin/members/meetings/${m.id}`); load(); } }} className="text-[#241019]/35 hover:text-red-600"><Trash2 size={14} /></button>
                </span>
              </div>
              {open === m.id && <AttendanceSheet m={m} members={d.members} onSaved={load} />}
              {mins === m.id && <MinutesEditor m={m} onSaved={load} />}
              {agenda === m.id && <AgendaEditor m={m} onSaved={load} />}
              {rsvp === m.id && <GatheringPanel m={m} onSaved={load} />}
            </div>
          ))}
          {!d.meetings.length && <p className="text-[13.5px] text-[#241019]/50">No meetings recorded this year.</p>}
        </div>
      </div>
      <div data-testid="attendance-flags" className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 self-start">
        <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2"><AlertTriangle size={17} className="text-[#B4247E]" /> Attendance flags</p>
        <p className="text-[12.5px] text-[#241019]/55 mb-4">Article V rules. Warning letters are emailed and $10 fines are added to the member's balance automatically.</p>
        {!d.flagged.length ? <p className="text-[13.5px] text-[#241019]/50">No members flagged.</p> : d.flagged.map((x) => (
          <div key={x.user_id} data-testid={`flagged-${x.user_id}`} className="py-2 border-b border-[#3B0A2E]/8 last:border-0">
            <p className="font-semibold text-[14px] text-[#3B0A2E]">{x.name} <span className="text-[12px] text-[#241019]/50 font-normal">· {x.consecutive_absences} in a row · {x.total_absences} this year</span></p>
            <div className="flex flex-wrap gap-1 mt-1">{x.flags.map((fl) => <span key={fl} className="text-[11.5px] bg-red-50 text-red-700 rounded-full px-2.5 py-0.5">{FLAG[fl]}</span>)}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
