import React, { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ChevronLeft, ChevronRight, CalendarDays, List } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';
import PageHero from '../components/PageHero';
import { SeatsBadge } from '../components/ProgramSignup';

const d = (s) => new Date(`${s}T12:00:00`);
const fmt = (s, opts = { month: 'short', day: 'numeric', year: 'numeric' }) => d(s).toLocaleDateString('en-US', opts);
export const sessionDates = (p) => (p.end_date && p.end_date !== p.start_date ? `${fmt(p.start_date, { month: 'short', day: 'numeric' })} – ${fmt(p.end_date)}` : fmt(p.start_date));
const iso = (y, m, day) => `${y}-${String(m + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
const COLORS = ['#B4247E', '#CBA24B', '#3B0A2E', '#3c7a2f', '#8a6a2c', '#53657d'];

function SessionCard({ p }) {
  const img = p.image_url ? (p.image_url.startsWith('/api/') ? mediaSrc(p.image_url) : p.image_url) : '';
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden flex flex-col sm:flex-row card-hover" data-testid="session-card">
      {img && <img src={img} alt={p.title} className="sm:w-48 h-40 sm:h-auto object-cover" />}
      <div className="p-6 flex-1 flex flex-col">
        {p.category && <span className="text-[11px] uppercase tracking-wide font-semibold text-[#B4247E] mb-1">{p.category}</span>}
        <h3 className="font-serif text-[21px] text-[#3B0A2E] font-semibold mb-1" data-testid="session-title">{p.title}</h3>
        <p className="text-[13.5px] text-[#3B0A2E] font-semibold flex items-center gap-1.5 mb-2" data-testid="session-dates"><CalendarDays size={14} className="text-[#B4247E]" /> {sessionDates(p)}{p.schedule ? ` · ${p.schedule}` : ''}</p>
        {p.summary && <p className="text-[13.5px] text-[#241019]/65 mb-3 line-clamp-2">{p.summary}</p>}
        <div className="mt-auto flex flex-wrap items-center gap-3">
          <SeatsBadge p={p} />
          <Link to={`/initiatives/${p.slug}#join`} data-testid="session-signup-link" className="btn-magenta rounded-full px-5 py-2 font-semibold text-[13px]">{p.full ? 'Join Waitlist' : 'Sign Up'}</Link>
        </div>
      </div>
    </div>
  );
}

function MonthGrid({ items, month, setMonth }) {
  const y = month.getFullYear(), m = month.getMonth();
  const days = new Date(y, m + 1, 0).getDate();
  const offset = new Date(y, m, 1).getDay();
  const today = new Date().toISOString().slice(0, 10);
  const color = Object.fromEntries(items.map((p, i) => [p.id, COLORS[i % COLORS.length]]));
  const on = (day) => items.filter((p) => { const s = iso(y, m, day); return s >= p.start_date && s <= (p.end_date || p.start_date); });
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-5" data-testid="sessions-calendar">
      <div className="flex items-center justify-between mb-4">
        <button onClick={() => setMonth(new Date(y, m - 1, 1))} data-testid="sessions-prev-month" className="p-2 rounded-full hover:bg-[#faf2f7]"><ChevronLeft size={18} /></button>
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold" data-testid="sessions-month-label">{month.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}</p>
        <button onClick={() => setMonth(new Date(y, m + 1, 1))} data-testid="sessions-next-month" className="p-2 rounded-full hover:bg-[#faf2f7]"><ChevronRight size={18} /></button>
      </div>
      <div className="grid grid-cols-7 gap-1 text-center text-[11px] uppercase tracking-wide text-[#241019]/45 mb-1">{['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((x) => <span key={x}>{x}</span>)}</div>
      <div className="grid grid-cols-7 gap-1">
        {Array.from({ length: offset }).map((_, i) => <div key={`e${i}`} />)}
        {Array.from({ length: days }, (_, i) => i + 1).map((day) => {
          const list = on(day);
          const isToday = iso(y, m, day) === today;
          return (
            <div key={day} className={`min-h-[78px] rounded-lg p-1.5 text-left ${list.length ? 'bg-[#fdf9fb]' : ''} ${isToday ? 'ring-2 ring-[#B4247E]/40' : 'border border-[#3B0A2E]/5'}`} data-testid="sessions-day">
              <span className="text-[11.5px] font-semibold text-[#3B0A2E]/70">{day}</span>
              {list.slice(0, 2).map((p) => (
                <Link key={p.id} to={`/initiatives/${p.slug}`} title={p.title} data-testid="sessions-day-event" className="block mt-0.5 truncate text-[10.5px] font-semibold text-white rounded px-1 py-0.5" style={{ background: color[p.id] }}>{p.title}</Link>
              ))}
              {list.length > 2 && <span className="text-[10px] text-[#241019]/50">+{list.length - 2} more</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default function Sessions() {
  const [items, setItems] = useState(null);
  const [view, setView] = useState('calendar');
  const [month, setMonth] = useState(() => { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), 1); });
  useEffect(() => {
    api.get('/sessions').then(({ data }) => {
      setItems(data.items);
      const first = data.items[0];
      const now = new Date().toISOString().slice(0, 10);
      if (first && first.start_date > now) setMonth(new Date(d(first.start_date).getFullYear(), d(first.start_date).getMonth(), 1));
    }).catch(() => setItems([]));
  }, []);
  const tabs = useMemo(() => [['calendar', 'Calendar', CalendarDays], ['list', 'List', List]], []);
  return (
    <div data-testid="sessions-page">
      <PageHero kicker="Plan ahead" title="Upcoming Sessions" subtitle="See when every program session starts, how many spots are left, and save your place." />
      <section className="py-14 lg:py-20">
        <div className="max-w-6xl mx-auto px-5 lg:px-8">
          <div className="flex gap-2 mb-6">
            {tabs.map(([v, l, Icon]) => (
              <button key={v} onClick={() => setView(v)} data-testid={`sessions-view-${v}`} className={`px-5 py-2 rounded-full text-[13.5px] font-semibold flex items-center gap-1.5 transition-colors ${view === v ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12'}`}><Icon size={15} /> {l}</button>
            ))}
          </div>
          {!items ? <Loader2 className="animate-spin text-[#B4247E]" /> : items.length === 0 ? (
            <p className="text-[15px] text-[#241019]/60 py-10" data-testid="sessions-empty">No upcoming sessions are scheduled yet. <Link to="/initiatives" className="text-[#B4247E] font-semibold">Browse our programs</Link>.</p>
          ) : view === 'calendar' ? (
            <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6 items-start">
              <MonthGrid items={items} month={month} setMonth={setMonth} />
              <div className="space-y-4">{items.slice(0, 4).map((p) => <SessionCard key={p.id} p={p} />)}</div>
            </div>
          ) : (
            <div className="grid gap-5" data-testid="sessions-list">{items.map((p) => <SessionCard key={p.id} p={p} />)}</div>
          )}
        </div>
      </section>
    </div>
  );
}
