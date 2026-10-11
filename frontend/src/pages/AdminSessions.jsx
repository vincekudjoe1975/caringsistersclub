import React, { useEffect, useState, useCallback } from 'react';
import { api, BACKEND_URL } from '../lib/api';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts';
import { useToast } from '../hooks/use-toast';
import { Loader2, Plus, Pencil, Trash2, CalendarDays, Clock, MapPin, Users } from 'lucide-react';

const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[14px] focus:outline-none focus:border-[#B4247E]';
const EMPTY = { date: '', start_time: '', end_time: '', location: '', seats: 0, notes: '' };
const t12 = (t) => { if (!t) return ''; const [h, m] = t.split(':').map(Number); return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`; };

function SessionForm({ pid, initial, onDone }) {
  const { toast } = useToast();
  const [f, setF] = useState({ ...EMPTY, ...initial });
  const set = (k) => (e) => setF({ ...f, [k]: k === 'seats' ? Math.max(0, parseInt(e.target.value || '0', 10)) : e.target.value });
  const save = async (e) => {
    e.preventDefault();
    const body = Object.fromEntries(Object.keys(EMPTY).map((k) => [k, f[k]]));
    try { initial.id ? await api.put(`/admin/sessions/${initial.id}`, body) : await api.post(`/admin/programs/${pid}/sessions`, body); toast({ title: 'Session saved' }); onDone(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <form onSubmit={save} data-testid="session-form" className="bg-[#fdf9fb] rounded-xl p-5 border border-[#B4247E]/15 grid sm:grid-cols-3 gap-3 animate-[fadeIn_.25s_ease]">
      <label className="text-[12.5px] font-semibold text-[#3B0A2E]">Date *<input required type="date" value={f.date} onChange={set('date')} data-testid="session-date-input" className={input} /></label>
      <label className="text-[12.5px] font-semibold text-[#3B0A2E]">Start time<input type="time" value={f.start_time} onChange={set('start_time')} data-testid="session-start-input" className={input} /></label>
      <label className="text-[12.5px] font-semibold text-[#3B0A2E]">End time<input type="time" value={f.end_time} onChange={set('end_time')} data-testid="session-end-input" className={input} /></label>
      <label className="text-[12.5px] font-semibold text-[#3B0A2E] sm:col-span-2">Location<input value={f.location} onChange={set('location')} maxLength={200} placeholder="Address or 'Online (Zoom)'" data-testid="session-location-input" className={input} /></label>
      <label className="text-[12.5px] font-semibold text-[#3B0A2E]">Seats (0 = unlimited)<input type="number" min="0" value={f.seats} onChange={set('seats')} data-testid="session-seats-input" className={input} /></label>
      <label className="text-[12.5px] font-semibold text-[#3B0A2E] sm:col-span-3">Notes (optional)<input value={f.notes} onChange={set('notes')} maxLength={500} placeholder="e.g. Bring a notebook" data-testid="session-notes-input" className={input} /></label>
      <div className="sm:col-span-3 flex gap-2">
        <button data-testid="session-save-btn" className="btn-magenta rounded-full px-6 py-2 text-[13px] font-semibold">Save session</button>
        <button type="button" onClick={onDone} data-testid="session-cancel-btn" className="rounded-full px-5 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E]">Cancel</button>
      </div>
    </form>
  );
}

const WD = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const bucket = (t) => { if (!t) return 'Time not set'; const h = parseInt(t.slice(0, 2), 10); return h < 12 ? 'Morning' : h < 17 ? 'Afternoon' : 'Evening'; };
function best(groups) {
  const rows = Object.entries(groups).map(([k, v]) => ({ k, rate: Math.round((100 * v.a) / v.m), n: v.n })).sort((x, y) => y.rate - x.rate || y.n - x.n);
  return rows;
}
function SessionInsights({ sessions }) {
  const marked = sessions.filter((s) => s.attended + s.no_show > 0);
  if (marked.length < 3) return <p data-testid="insights-pending" className="px-5 py-4 text-[12.5px] text-[#241019]/55 border-t border-[#3B0A2E]/6">Attendance insights appear once at least 3 sessions have attendance marked ({marked.length}/3 so far).</p>;
  const byDay = {}; const byTime = {};
  marked.forEach((s) => {
    const add = (g, k) => { g[k] = g[k] || { a: 0, m: 0, n: 0 }; g[k].a += s.attended; g[k].m += s.attended + s.no_show; g[k].n += 1; };
    add(byDay, WD[new Date(`${s.date}T12:00:00`).getDay()]); add(byTime, bucket(s.start_time));
  });
  const days = best(byDay); const times = best(byTime);
  const data = marked.map((s) => ({ date: new Date(`${s.date}T12:00:00`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' }), rate: s.attendance_pct, label: s.label }));
  const Pill = ({ title, rows, tid }) => (
    <div className="flex-1 min-w-[220px] rounded-xl bg-[#fdf9fb] p-4" data-testid={tid}>
      <p className="text-[11.5px] uppercase tracking-wide text-[#241019]/50 mb-1">{title}</p>
      <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold">{rows[0].k} <span className="text-[14px] text-[#B4247E]">{rows[0].rate}%</span></p>
      <p className="text-[12px] text-[#241019]/55 mt-1">{rows.slice(1).map((r) => `${r.k} ${r.rate}%`).join(' · ') || 'Only one option so far'}</p>
    </div>
  );
  return (
    <div className="border-t border-[#3B0A2E]/6 px-5 py-5" data-testid="session-insights">
      <p className="font-serif text-[17px] text-[#3B0A2E] font-semibold mb-3">Attendance trend</p>
      <div className="h-52" data-testid="insights-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data} margin={{ top: 6, right: 12, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#3B0A2E" strokeOpacity={0.06} vertical={false} />
            <XAxis dataKey="date" tickLine={false} axisLine={false} tick={{ fontSize: 11.5, fill: '#6b5560' }} />
            <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} tickLine={false} axisLine={false} tick={{ fontSize: 11, fill: '#8a7380' }} />
            <Tooltip formatter={(v) => [`${v}%`, 'Attendance']} labelFormatter={(l, p) => p?.[0]?.payload?.label || l} />
            <Line type="monotone" dataKey="rate" stroke="#B4247E" strokeWidth={2.5} dot={{ r: 4, fill: '#3B0A2E' }} activeDot={{ r: 6 }} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="flex flex-wrap gap-3 mt-4">
        <Pill title="Best day of the week" rows={days} tid="insights-best-day" />
        <Pill title="Best time of day" rows={times} tid="insights-best-time" />
      </div>
    </div>
  );
}

function SessionReport({ pid }) {
  const [r, setR] = useState(null);
  useEffect(() => { api.get(`/admin/programs/${pid}/session-report`).then(({ data }) => setR(data)); }, [pid]);
  if (!r) return null;
  const pct = (v) => (v == null ? '—' : `${v}%`);
  return (
    <div data-testid="session-report" className="mt-8 rounded-xl border border-[#3B0A2E]/10 overflow-hidden">
      <div className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 bg-[#fdf9fb]">
        <div><p className="font-serif text-[18px] text-[#3B0A2E] font-semibold">Attendance by session</p>
          <p className="text-[12.5px] text-[#241019]/60">Overall: {r.totals.attended} attended · {r.totals.no_show} absent · {r.totals.unmarked} unmarked · <span data-testid="session-report-pct">{pct(r.totals.attendance_pct)}</span> attendance</p></div>
        <a data-testid="session-report-csv" href={`${BACKEND_URL}/api/admin/programs/${pid}/session-attendance.csv`} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E]">Download CSV</a>
      </div>
      <div className="overflow-x-auto"><table className="w-full text-[13px]">
        <thead><tr className="text-left text-[11.5px] uppercase tracking-wide text-[#241019]/50">{['Session', 'Signed up', 'Attended', 'Absent', 'Unmarked', 'Attendance'].map((h) => <th key={h} className="px-5 py-2.5 font-semibold">{h}</th>)}</tr></thead>
        <tbody>{r.sessions.map((s) => (
          <tr key={s.id} data-testid={`session-report-row-${s.id}`} className="border-t border-[#3B0A2E]/6">
            <td className="px-5 py-2.5 text-[#3B0A2E] font-semibold">{s.label}</td><td className="px-5">{s.signed_up}{s.seats ? ` / ${s.seats}` : ''}</td>
            <td className="px-5 text-green-700">{s.attended}</td><td className="px-5 text-red-600">{s.no_show}</td><td className="px-5 text-[#241019]/55">{s.unmarked}</td>
            <td className="px-5 font-semibold">{pct(s.attendance_pct)}</td>
          </tr>))}</tbody>
      </table></div>
      <SessionInsights sessions={r.sessions} />
    </div>
  );
}

export default function AdminSessions() {
  const { toast } = useToast();
  const [programs, setPrograms] = useState([]);
  const [pid, setPid] = useState('');
  const [rows, setRows] = useState(null);
  const [edit, setEdit] = useState(null);
  useEffect(() => { api.get('/admin/programs').then(({ data }) => { const l = data.items || data || []; setPrograms(l); if (l[0]) setPid(l[0].id); }); }, []);
  const load = useCallback(() => { if (pid) api.get(`/admin/programs/${pid}/sessions`).then(({ data }) => setRows(data.items)); }, [pid]);
  useEffect(() => { setRows(null); setEdit(null); load(); }, [load]);
  const del = async (s) => {
    if (!window.confirm('Delete this session?')) return;
    try { await api.delete(`/admin/sessions/${s.id}`); load(); } catch (ex) { toast({ title: 'Cannot delete', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const today = new Date().toISOString().slice(0, 10);
  return (
    <div data-testid="admin-sessions" className="bg-white rounded-2xl p-7 border border-[#3B0A2E]/8">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div><h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold flex items-center gap-2"><CalendarDays size={20} className="text-[#B4247E]" /> Program sessions</h2>
          <p className="text-[13.5px] text-[#241019]/60 max-w-xl">Add dated sessions to any program. They appear on the public Sessions calendar, and people choose a session when they sign up.</p></div>
        <select data-testid="sessions-program-select" value={pid} onChange={(e) => setPid(e.target.value)} className="rounded-full border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] font-semibold text-[#3B0A2E] min-w-[240px]">
          {programs.map((p) => <option key={p.id} value={p.id}>{p.title}{p.published === false ? ' (draft)' : ''}</option>)}
        </select>
      </div>
      {edit ? <SessionForm pid={pid} initial={edit} onDone={() => { setEdit(null); load(); }} /> : (
        <button data-testid="session-add-btn" onClick={() => setEdit({})} disabled={!pid} className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-50"><Plus size={15} /> Add session</button>
      )}
      {pid && rows && rows.length > 0 && <SessionReport pid={pid} key={`${pid}-${rows.map((r) => r.signups).join('.')}`} />}
      <div className="mt-6 divide-y divide-[#3B0A2E]/8">
        {rows === null ? <Loader2 className="animate-spin text-[#B4247E]" /> : !rows.length ? <p data-testid="sessions-admin-empty" className="text-[13.5px] text-[#241019]/55 py-4">No sessions yet for this program.</p> : rows.map((s) => (
          <div key={s.id} data-testid={`session-row-${s.id}`} className={`py-3.5 flex flex-wrap items-center gap-x-6 gap-y-1 ${s.date < today ? 'opacity-50' : ''}`}>
            <span className="font-semibold text-[14px] text-[#3B0A2E] w-44">{new Date(`${s.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>
            <span className="text-[13px] text-[#241019]/70 flex items-center gap-1 w-40"><Clock size={13} /> {s.start_time ? `${t12(s.start_time)}${s.end_time ? ` – ${t12(s.end_time)}` : ''}` : 'Time TBA'}</span>
            <span className="text-[13px] text-[#241019]/70 flex items-center gap-1 flex-1 min-w-[160px]"><MapPin size={13} /> {s.location || 'Location TBA'}</span>
            <span data-testid={`session-seats-${s.id}`} className="text-[13px] text-[#241019]/70 flex items-center gap-1"><Users size={13} /> {s.signups} signed up{s.seats ? ` / ${s.seats}` : ''}</span>
            <span className="flex gap-3 text-[#241019]/50">
              <a data-testid={`session-sheet-${s.id}`} href={`/session-sheet/${s.id}`} target="_blank" rel="noopener noreferrer" className="text-[12.5px] font-semibold text-[#3B0A2E] hover:underline">Sign-in sheet</a>
              <a data-testid={`session-checkin-${s.id}`} href={`/session-checkin/${s.id}`} className="text-[12.5px] font-semibold text-[#B4247E] hover:underline">Check-in</a>
              <button data-testid={`session-edit-${s.id}`} onClick={() => setEdit(s)} className="hover:text-[#B4247E]"><Pencil size={15} /></button>
              <button data-testid={`session-delete-${s.id}`} onClick={() => del(s)} className="hover:text-red-600"><Trash2 size={15} /></button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
