import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { fmtDate, eventImg } from './Events';
import { Loader2, Plus, Pencil, Trash2, Users, Download, X, UploadCloud, CalendarDays, MapPin, Clock, BellRing } from 'lucide-react';

const EMPTY = { title: '', date: '', time: '', location: '', category: '', description: '', image_url: '', capacity: 50 };
const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';
const todayStr = new Date().toISOString().slice(0, 10);

function Field({ label, children }) {
  return <div><label className="text-[13px] font-semibold text-[#3B0A2E]">{label}</label>{children}</div>;
}

function EventForm({ initial, onClose, onSaved }) {
  const [form, setForm] = useState({ ...EMPTY, ...initial });
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const { toast } = useToast();
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file); fd.append('category', 'event'); fd.append('title', form.title || file.name);
    setUploading(true);
    try {
      const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setForm((f) => ({ ...f, image_url: data.url }));
    } catch (err) {
      toast({ title: 'Image upload failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setUploading(false); }
  };

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const body = { ...form, capacity: Number(form.capacity) || 1 };
      if (initial.id) await api.put(`/admin/events/${initial.id}`, body);
      else await api.post('/admin/events', body);
      toast({ title: initial.id ? 'Event updated' : 'Event created', description: 'It is now live on the Events page.' });
      onSaved();
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setSaving(false); }
  };

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} data-testid="event-form"
        className="bg-white rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto p-7 space-y-4">
        <div className="flex items-start justify-between">
          <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{initial.id ? 'Edit event' : 'New event'}</h3>
          <button type="button" onClick={onClose} className="text-[#241019]/50 hover:text-[#3B0A2E]"><X size={20} /></button>
        </div>
        <Field label="Title *"><input required value={form.title} onChange={set('title')} data-testid="event-title-input" className={input} /></Field>
        <div className="grid sm:grid-cols-3 gap-4">
          <Field label="Date *"><input required type="date" min={initial.id ? undefined : todayStr} value={form.date} onChange={set('date')} data-testid="event-date-input" className={input} /></Field>
          <Field label="Time"><input value={form.time} onChange={set('time')} placeholder="6:00 PM" data-testid="event-time-input" className={input} /></Field>
          <Field label="Capacity *"><input required type="number" min={1} value={form.capacity} onChange={set('capacity')} data-testid="event-capacity-input" className={input} /></Field>
        </div>
        <div className="grid sm:grid-cols-[2fr_1fr] gap-4">
          <Field label="Location"><input value={form.location} onChange={set('location')} placeholder="Venue, City or Virtual (Zoom)" data-testid="event-location-input" className={input} /></Field>
          <Field label="Category"><input value={form.category} onChange={set('category')} placeholder="Workshop" data-testid="event-category-input" className={input} /></Field>
        </div>
        <Field label="Description"><textarea rows={4} value={form.description} onChange={set('description')} data-testid="event-description-input" className={`${input} resize-none`} /></Field>
        <div className="flex items-center gap-4">
          <img src={eventImg(form.image_url)} alt="" className="w-28 h-20 rounded-lg object-cover border border-[#3B0A2E]/10" />
          <label className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-2 cursor-pointer">
            {uploading ? <Loader2 size={15} className="animate-spin" /> : <UploadCloud size={15} />} {form.image_url ? 'Replace image' : 'Upload image'}
            <input type="file" accept="image/*" className="hidden" data-testid="event-image-input" onChange={(e) => upload(e.target.files?.[0])} />
          </label>
          {!form.image_url && <span className="text-[12px] text-[#241019]/45">A default photo is used if none is uploaded.</span>}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose} className="px-5 py-2.5 rounded-full text-[13.5px] font-semibold text-[#3B0A2E]" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>Cancel</button>
          <button type="submit" disabled={saving || uploading} data-testid="event-save-btn" className="btn-magenta px-6 py-2.5 rounded-full text-[13.5px] font-semibold flex items-center gap-2 disabled:opacity-60">
            {saving ? <Loader2 size={15} className="animate-spin" /> : null} {initial.id ? 'Save changes' : 'Create event'}
          </button>
        </div>
      </form>
    </div>
  );
}

function RsvpPanel({ ev, onClose, onChanged }) {
  const [items, setItems] = useState(null);
  const { toast } = useToast();
  const load = useCallback(async () => {
    const { data } = await api.get(`/admin/events/${ev.id}/rsvps`);
    setItems(data.items || []);
  }, [ev.id]);
  useEffect(() => { load().catch(() => setItems([])); }, [load]);

  const exportCsv = async () => {
    try {
      const res = await api.get(`/admin/events/${ev.id}/rsvps/export`, { responseType: 'blob' });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement('a');
      a.href = url; a.download = `rsvps-${ev.title.replace(/[^A-Za-z0-9]+/g, '-')}.csv`; a.click();
      URL.revokeObjectURL(url);
    } catch { toast({ title: 'Export failed', variant: 'destructive' }); }
  };

  const remove = async (r) => {
    if (!window.confirm(`Remove ${r.name}'s RSVP?`)) return;
    try { await api.delete(`/admin/events/${ev.id}/rsvps/${r.id}`); load(); onChanged(); }
    catch { toast({ title: 'Remove failed', variant: 'destructive' }); }
  };

  const seats = (items || []).reduce((s, r) => s + (r.guests || 1), 0);
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(41,6,31,0.6)' }} onClick={onClose}>
      <div onClick={(e) => e.stopPropagation()} className="bg-white rounded-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto" data-testid="rsvp-panel">
        <div className="p-6 flex items-start justify-between" style={{ background: '#faf2f7' }}>
          <div>
            <h3 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">{ev.title}</h3>
            <p className="text-[#241019]/60 text-[13px]">{fmtDate(ev.date)} &middot; {seats} of {ev.capacity} seats taken</p>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={exportCsv} data-testid="rsvp-export-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full bg-white text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><Download size={14} /> CSV</button>
            <button onClick={onClose} className="text-[#241019]/50 hover:text-[#3B0A2E]"><X size={20} /></button>
          </div>
        </div>
        {items === null ? <div className="flex justify-center py-10"><Loader2 className="animate-spin text-[#B4247E]" /></div>
          : items.length === 0 ? <p className="text-center text-[13px] text-[#241019]/50 p-10">No RSVPs yet.</p> : (
          <table className="w-full text-left">
            <thead><tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide">
              <th className="px-5 py-3 font-semibold">Guest</th><th className="px-5 py-3 font-semibold">Party</th><th className="px-5 py-3 font-semibold">RSVP'd</th><th className="px-5 py-3 font-semibold">Reminder</th><th />
            </tr></thead>
            <tbody>{items.map((r) => (
              <tr key={r.id} className="border-t border-[#3B0A2E]/8 text-[13px]" data-testid="rsvp-row">
                <td className="px-5 py-3"><p className="font-semibold text-[#3B0A2E]">{r.name}</p><p className="text-[#241019]/55 text-[12px]">{r.email}</p></td>
                <td className="px-5 py-3">{r.guests}</td>
                <td className="px-5 py-3 text-[#241019]/65">{new Date(r.created_at).toLocaleDateString()}</td>
                <td className="px-5 py-3 text-[#241019]/65">{r.reminder_sent ? <span className="flex items-center gap-1 text-[#3c7a2f]"><BellRing size={13} /> Sent</span> : 'Pending'}</td>
                <td className="px-5 py-3 text-right"><button onClick={() => remove(r)} data-testid="rsvp-remove-btn" className="text-red-500 hover:text-red-700"><Trash2 size={15} /></button></td>
              </tr>
            ))}</tbody>
          </table>
        )}
      </div>
    </div>
  );
}

function AdminEventRow({ ev, onEdit, onRsvps, onDelete }) {
  const past = ev.date < todayStr;
  const pct = Math.min(100, Math.round((ev.seats_taken / ev.capacity) * 100));
  return (
    <div className={`bg-white rounded-2xl border border-[#3B0A2E]/8 p-4 flex flex-col sm:flex-row gap-4 sm:items-center ${past ? 'opacity-60' : ''}`} data-testid="admin-event-row">
      <img src={eventImg(ev.image_url)} alt="" className="w-full sm:w-32 h-24 rounded-xl object-cover" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h4 className="font-serif text-[18px] text-[#3B0A2E] font-semibold truncate">{ev.title}</h4>
          {past && <span className="text-[10.5px] font-semibold px-2 py-0.5 rounded-full bg-[#eef1f5] text-[#53657d]">Past</span>}
        </div>
        <p className="text-[12.5px] text-[#241019]/60 flex flex-wrap gap-x-4 gap-y-1">
          <span className="flex items-center gap-1"><CalendarDays size={13} /> {fmtDate(ev.date)}</span>
          {ev.time && <span className="flex items-center gap-1"><Clock size={13} /> {ev.time}</span>}
          {ev.location && <span className="flex items-center gap-1"><MapPin size={13} /> {ev.location}</span>}
        </p>
        <div className="mt-2.5 flex items-center gap-3">
          <div className="h-2 flex-1 max-w-[220px] rounded-full bg-[#eadfe6] overflow-hidden"><div className="h-full rounded-full" style={{ width: `${pct}%`, background: '#B4247E' }} /></div>
          <span className="text-[12px] font-semibold text-[#3B0A2E]" data-testid="admin-event-seats">{ev.seats_taken}/{ev.capacity} seats &middot; {ev.rsvp_count} RSVPs</span>
        </div>
      </div>
      <div className="flex items-center gap-2">
        <button onClick={onRsvps} data-testid="admin-event-rsvps-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><Users size={14} /> RSVPs</button>
        <button onClick={onEdit} data-testid="admin-event-edit-btn" className="p-2 text-[#3B0A2E] hover:text-[#B4247E]"><Pencil size={16} /></button>
        <button onClick={onDelete} data-testid="admin-event-delete-btn" className="p-2 text-red-500 hover:text-red-700"><Trash2 size={16} /></button>
      </div>
    </div>
  );
}

export default function AdminEvents() {
  const [events, setEvents] = useState(null);
  const [editing, setEditing] = useState(null);
  const [viewing, setViewing] = useState(null);
  const { toast } = useToast();

  const load = useCallback(async () => {
    try { const { data } = await api.get('/admin/events'); setEvents(data.items || []); }
    catch (e) { console.error('AdminEvents: load failed', e); setEvents([]); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const remove = async (ev) => {
    if (!window.confirm(`Delete "${ev.title}" and all ${ev.rsvp_count} RSVPs? This cannot be undone.`)) return;
    try { await api.delete(`/admin/events/${ev.id}`); toast({ title: 'Event deleted' }); load(); }
    catch { toast({ title: 'Delete failed', variant: 'destructive' }); }
  };

  return (
    <div data-testid="admin-events">
      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Events</h2>
          <p className="text-[#241019]/60 text-[13.5px]">Upcoming events appear on the public Events page. Guests get a confirmation email and a reminder the day before.</p>
        </div>
        <button onClick={() => setEditing({})} data-testid="new-event-btn" className="btn-magenta rounded-full px-5 py-2.5 text-[13.5px] font-semibold flex items-center gap-2"><Plus size={16} /> New Event</button>
      </div>
      {events === null ? <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={30} /></div>
        : events.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8 text-[#241019]/55 text-[14px]">No events yet. Click "New Event" to publish your first one.</div>
        ) : (
          <div className="space-y-3">{events.map((ev) => (
            <AdminEventRow key={ev.id} ev={ev} onEdit={() => setEditing(ev)} onRsvps={() => setViewing(ev)} onDelete={() => remove(ev)} />
          ))}</div>
        )}
      {editing && <EventForm initial={editing} onClose={() => setEditing(null)} onSaved={() => { setEditing(null); load(); }} />}
      {viewing && <RsvpPanel ev={viewing} onClose={() => setViewing(null)} onChanged={load} />}
    </div>
  );
}
