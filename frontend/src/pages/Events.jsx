import React, { useEffect, useState, useCallback } from 'react';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { Calendar, MapPin, Clock, Users, Loader2, CheckCircle2, CalendarHeart } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useToast } from '../hooks/use-toast';
import { api, mediaSrc } from '../lib/api';

const FALLBACK_IMG = 'https://images.pexels.com/photos/7648057/pexels-photo-7648057.jpeg?auto=compress&cs=tinysrgb&h=650&w=940';

export function fmtDate(d) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export const eventImg = (url) => (!url ? FALLBACK_IMG : url.startsWith('/api/') ? mediaSrc(url) : url);

const errMsg = (err) => (err?.response?.status === 429
  ? "You've sent a few requests in a row. Please wait a minute and try again."
  : err?.response?.data?.detail || 'Something went wrong. Please check your connection and try again.');

function EventCard({ ev, onRsvp }) {
  const full = ev.spots_left <= 0;
  return (
    <div className="card-hover bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 grid md:grid-cols-[300px_1fr]" data-testid="event-card">
      <div className="img-zoom h-56 md:h-full">
        <img src={eventImg(ev.image_url)} alt={ev.title} className="w-full h-full object-cover" />
      </div>
      <div className="p-7 lg:p-9 flex flex-col justify-center">
        <div className="flex items-center gap-3 mb-3">
          {ev.category && <span className="text-[11px] font-semibold px-3 py-1 rounded-full text-white" style={{ background: '#B4247E' }}>{ev.category}</span>}
          <span className="flex items-center gap-1.5 text-[#241019]/60 text-[13px]" data-testid="event-spots-left">
            <Users size={14} /> {full ? 'Fully booked' : `${ev.spots_left} of ${ev.capacity} spots left`}
          </span>
        </div>
        <h3 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">{ev.title}</h3>
        {ev.description && <p className="text-[#241019]/70 text-[14.5px] leading-relaxed mb-5 max-w-2xl whitespace-pre-line">{ev.description}</p>}
        <div className="flex flex-wrap gap-x-7 gap-y-2 text-[#3B0A2E] text-[13.5px] mb-6">
          <span className="flex items-center gap-2"><Calendar size={16} className="text-[#CBA24B]" /> {fmtDate(ev.date)}</span>
          {ev.time && <span className="flex items-center gap-2"><Clock size={16} className="text-[#CBA24B]" /> {ev.time}</span>}
          {ev.location && <span className="flex items-center gap-2"><MapPin size={16} className="text-[#CBA24B]" /> {ev.location}</span>}
        </div>
        <button onClick={() => onRsvp(ev)} disabled={full} data-testid="event-rsvp-btn"
          className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] self-start disabled:opacity-50 disabled:cursor-not-allowed">
          {full ? 'Event Full' : 'RSVP Now'}
        </button>
      </div>
    </div>
  );
}

function RsvpForm({ ev, onDone }) {
  const [form, setForm] = useState({ name: '', email: '', guests: 1 });
  const [sending, setSending] = useState(false);
  const [done, setDone] = useState(false);
  const { toast } = useToast();
  const maxGuests = Math.min(10, ev.spots_left);

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post(`/events/${ev.id}/rsvp`, { ...form, guests: Number(form.guests) || 1 });
      setDone(true);
      onDone();
    } catch (err) {
      toast({ title: 'RSVP not completed', description: errMsg(err), variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  if (done) {
    return (
      <div className="text-center py-4" data-testid="rsvp-success">
        <CheckCircle2 size={48} className="text-[#B4247E] mx-auto mb-3" />
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1">You're registered!</p>
        <p className="text-[13.5px] text-[#241019]/65">A confirmation is on its way to <strong>{form.email}</strong>, and we'll send a reminder the day before.</p>
      </div>
    );
  }

  const input = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';
  return (
    <form onSubmit={submit} className="space-y-4 mt-2">
      <p className="text-[13px] text-[#241019]/60">{fmtDate(ev.date)}{ev.time && <> &middot; {ev.time}</>}{ev.location && <> &middot; {ev.location}</>}</p>
      <div>
        <label className="text-[13px] font-semibold text-[#3B0A2E]">Full Name</label>
        <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="rsvp-name-input" className={input} />
      </div>
      <div>
        <label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label>
        <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="rsvp-email-input" className={input} />
      </div>
      <div>
        <label className="text-[13px] font-semibold text-[#3B0A2E]">Number of Guests (including you)</label>
        <input type="number" min={1} max={maxGuests} value={form.guests} onChange={(e) => setForm({ ...form, guests: e.target.value })} data-testid="rsvp-guests-input" className={input} />
      </div>
      <button type="submit" disabled={sending} data-testid="rsvp-submit-btn" className="btn-magenta rounded-full w-full py-3 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
        {sending ? <><Loader2 size={16} className="animate-spin" /> Confirming…</> : 'Confirm RSVP'}
      </button>
    </form>
  );
}

export default function Events() {
  const [events, setEvents] = useState(null);
  const [selected, setSelected] = useState(null);

  const load = useCallback(async () => {
    try {
      const { data } = await api.get('/events');
      setEvents(data.items || []);
    } catch (e) {
      console.error('Events: failed to load', e);
      setEvents([]);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  return (
    <div>
      <PageHero
        kicker="Events & Programs Hub"
        title="Upcoming events & workshops"
        subtitle="Join us at summits, workshops, service drives, and mixers designed to connect and elevate our sisterhood."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 space-y-7">
          {events === null ? (
            <div className="flex justify-center py-16"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
          ) : events.length === 0 ? (
            <div className="bg-white rounded-2xl p-14 text-center border border-[#3B0A2E]/8" data-testid="events-empty">
              <CalendarHeart size={44} className="text-[#B4247E] mx-auto mb-4" />
              <h3 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-2">New events are coming soon</h3>
              <p className="text-[#241019]/65 text-[14.5px]">We're planning our next gatherings. Check back shortly or join our sisterhood to hear first.</p>
            </div>
          ) : events.map((ev, i) => (
            <Reveal key={ev.id} delay={(i % 2) * 100}>
              <EventCard ev={ev} onRsvp={setSelected} />
            </Reveal>
          ))}
        </div>
      </section>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-serif text-[22px] text-[#3B0A2E]">RSVP: {selected?.title}</DialogTitle>
          </DialogHeader>
          {selected && <RsvpForm key={selected.id} ev={selected} onDone={load} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}
