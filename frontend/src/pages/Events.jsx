import React, { useState } from 'react';
import { events } from '../mock/mock';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { Calendar, MapPin, Clock, Users, X } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { useToast } from '../hooks/use-toast';

function fmtDate(d) {
  return new Date(d + 'T00:00:00').toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function Events() {
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState({ name: '', email: '', guests: 1 });
  const { toast } = useToast();

  const submitRsvp = (e) => {
    e.preventDefault();
    toast({ title: 'RSVP confirmed! (demo)', description: `You're registered for "${selected.title}". A confirmation would be emailed to ${form.email}.` });
    setSelected(null);
    setForm({ name: '', email: '', guests: 1 });
  };

  return (
    <div>
      <PageHero
        kicker="Events & Programs Hub"
        title="Upcoming events & workshops"
        subtitle="Join us at summits, workshops, service drives, and mixers designed to connect and elevate our sisterhood."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-7xl mx-auto px-5 lg:px-8 space-y-7">
          {events.map((ev, i) => (
            <Reveal key={ev.id} delay={(i % 2) * 100}>
              <div className="card-hover bg-white rounded-2xl overflow-hidden border border-[#3B0A2E]/8 grid md:grid-cols-[300px_1fr]">
                <div className="img-zoom h-56 md:h-full">
                  <img src={ev.image} alt={ev.title} className="w-full h-full object-cover" />
                </div>
                <div className="p-7 lg:p-9 flex flex-col justify-center">
                  <div className="flex items-center gap-3 mb-3">
                    <span className="text-[11px] font-semibold px-3 py-1 rounded-full text-white" style={{ background: '#B4247E' }}>{ev.category}</span>
                    <span className="flex items-center gap-1.5 text-[#241019]/60 text-[13px]"><Users size={14} /> {ev.spots} spots</span>
                  </div>
                  <h3 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-3">{ev.title}</h3>
                  <p className="text-[#241019]/70 text-[14.5px] leading-relaxed mb-5 max-w-2xl">{ev.desc}</p>
                  <div className="flex flex-wrap gap-x-7 gap-y-2 text-[#3B0A2E] text-[13.5px] mb-6">
                    <span className="flex items-center gap-2"><Calendar size={16} className="text-[#CBA24B]" /> {fmtDate(ev.date)}</span>
                    <span className="flex items-center gap-2"><Clock size={16} className="text-[#CBA24B]" /> {ev.time}</span>
                    <span className="flex items-center gap-2"><MapPin size={16} className="text-[#CBA24B]" /> {ev.location}</span>
                  </div>
                  <button onClick={() => setSelected(ev)} className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] self-start">
                    RSVP Now
                  </button>
                </div>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="font-serif text-[22px] text-[#3B0A2E]">RSVP: {selected?.title}</DialogTitle>
          </DialogHeader>
          {selected && (
            <form onSubmit={submitRsvp} className="space-y-4 mt-2">
              <p className="text-[13px] text-[#241019]/60">{fmtDate(selected.date)} &middot; {selected.time} &middot; {selected.location}</p>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Full Name</label>
                <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label>
                <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Number of Guests</label>
                <input type="number" min={1} max={10} value={form.guests} onChange={(e) => setForm({ ...form, guests: e.target.value })}
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <button type="submit" className="btn-magenta rounded-full w-full py-3 font-semibold">Confirm RSVP</button>
            </form>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
