import React, { useEffect, useState } from 'react';
import { CalendarDays, Vote, Cake, Megaphone, Star, FileText, MapPin, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../../lib/api';

const day = (d) => new Date(`${d}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
const hm = (t) => (t ? new Date(`2000-01-01T${t}`).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : '');
const stamp = (iso) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });

const Section = ({ icon: Icon, title, items, empty, testid, children }) => (
  <section data-testid={testid} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 min-w-0">
    <h3 className="font-semibold text-[#3B0A2E] flex items-center gap-2 mb-3"><Icon size={16} className="text-[#B4247E]" /> {title}<span className="ml-auto text-[12.5px] font-semibold text-[#241019]/45">{items.length}</span></h3>
    {items.length ? <ul className="space-y-2.5">{children}</ul> : <p className="text-[13.5px] text-[#241019]/55">{empty}</p>}
  </section>
);

const Row = ({ main, sub }) => (
  <li className="text-[14px] leading-snug"><p className="text-[#241019] font-medium break-words">{main}</p>{sub && <p className="text-[13px] text-[#241019]/55 mt-0.5 break-words">{sub}</p>}</li>
);

export const ThisWeek = () => {
  const [w, setW] = useState(null);
  useEffect(() => { api.get('/members/this-week').then(({ data }) => setW(data)).catch(() => setW(false)); }, []);
  if (w === null) return <div className="py-16 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  if (!w) return <p className="text-[#241019]/60">Could not load this week's summary.</p>;
  const events = [...w.gatherings.map((g) => ({ k: `g${g.id}`, d: g.date, main: g.title, sub: `${day(g.date)}${g.time ? ` · ${hm(g.time)}` : ''}${g.location ? ` · ${g.location}` : ''}` })),
    ...w.sessions.map((s) => ({ k: `s${s.id}`, d: s.date, main: s.program, sub: `${day(s.date)}${s.start_time ? ` · ${hm(s.start_time)}` : ''}${s.location ? ` · ${s.location}` : ''}` }))].sort((a, b) => a.d.localeCompare(b.d));
  return (
    <div data-testid="this-week">
      <p className="text-[12.5px] uppercase tracking-[0.18em] text-[#B4247E] font-semibold">Week of {day(w.week_of)}</p>
      <h2 className="font-serif text-[30px] text-[#3B0A2E] font-semibold mt-1 mb-6">This week with the Club</h2>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Section testid="week-events" icon={CalendarDays} title="Gatherings & sessions" items={events} empty="Nothing on the calendar this week.">
          {events.map((e) => <Row key={e.k} main={e.main} sub={<><MapPin size={12} className="inline -mt-0.5 mr-1" />{e.sub}</>} />)}
        </Section>
        <Section testid="week-votes" icon={Vote} title="Open votes" items={w.votes} empty="No votes open right now.">
          {w.votes.map((v) => <Row key={v.id} main={v.title} sub={`Closes ${stamp(v.closes_at)}`} />)}
        </Section>
        <Section testid="week-birthdays" icon={Cake} title="Birthdays" items={w.birthdays} empty="No birthdays this week.">
          {w.birthdays.map((b) => <li key={`${b.user_id}${b.date}`} className="text-[14px]"><Link data-testid={`week-bday-${b.user_id}`} to={`/birthday-wishes/${b.user_id}`} className="font-medium text-[#3B0A2E] hover:text-[#B4247E] transition-colors">{b.name}</Link><span className="text-[13px] text-[#241019]/55"> · {day(b.date)}</span></li>)}
        </Section>
        <Section testid="week-news" icon={Megaphone} title="New announcements" items={w.announcements} empty="No new announcements this past week.">
          {w.announcements.map((a) => <Row key={a.id} main={a.title} sub={stamp(a.created_at)} />)}
        </Section>
        {(w.spotlights.length > 0 || w.minutes.length > 0) && (
          <Section testid="week-more" icon={Star} title="Spotlights & minutes" items={[...w.spotlights, ...w.minutes]} empty="">
            {w.spotlights.map((s) => <Row key={s.id} main={`Sister spotlight: ${s.name}`} sub="See the Spotlights tab" />)}
            {w.minutes.map((m) => <Row key={m.id} main={<><FileText size={13} className="inline -mt-0.5 mr-1" />Minutes approved: {m.title}</>} sub={day(m.date)} />)}
          </Section>
        )}
      </div>
    </div>
  );
};
