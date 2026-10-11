import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
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
      <div className="mt-6 divide-y divide-[#3B0A2E]/8">
        {rows === null ? <Loader2 className="animate-spin text-[#B4247E]" /> : !rows.length ? <p data-testid="sessions-admin-empty" className="text-[13.5px] text-[#241019]/55 py-4">No sessions yet for this program.</p> : rows.map((s) => (
          <div key={s.id} data-testid={`session-row-${s.id}`} className={`py-3.5 flex flex-wrap items-center gap-x-6 gap-y-1 ${s.date < today ? 'opacity-50' : ''}`}>
            <span className="font-semibold text-[14px] text-[#3B0A2E] w-44">{new Date(`${s.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' })}</span>
            <span className="text-[13px] text-[#241019]/70 flex items-center gap-1 w-40"><Clock size={13} /> {s.start_time ? `${t12(s.start_time)}${s.end_time ? ` – ${t12(s.end_time)}` : ''}` : 'Time TBA'}</span>
            <span className="text-[13px] text-[#241019]/70 flex items-center gap-1 flex-1 min-w-[160px]"><MapPin size={13} /> {s.location || 'Location TBA'}</span>
            <span data-testid={`session-seats-${s.id}`} className="text-[13px] text-[#241019]/70 flex items-center gap-1"><Users size={13} /> {s.signups} signed up{s.seats ? ` / ${s.seats}` : ''}</span>
            <span className="flex gap-3 text-[#241019]/50">
              <button data-testid={`session-edit-${s.id}`} onClick={() => setEdit(s)} className="hover:text-[#B4247E]"><Pencil size={15} /></button>
              <button data-testid={`session-delete-${s.id}`} onClick={() => del(s)} className="hover:text-red-600"><Trash2 size={15} /></button>
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
