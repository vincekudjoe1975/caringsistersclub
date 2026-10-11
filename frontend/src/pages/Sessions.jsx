import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ChevronLeft, ChevronRight, CalendarDays, List, CalendarPlus, Link2, Check, Clock, MapPin, X, Users } from 'lucide-react';
import { api, mediaSrc, BACKEND_URL } from '../lib/api';
import PageHero from '../components/PageHero';

const d = (s) => new Date(`${s}T12:00:00`);
const fmt = (s, opts = { month: 'short', day: 'numeric', year: 'numeric' }) => d(s).toLocaleDateString('en-US', opts);
export const sessionDates = (p) => (p.end_date && p.end_date !== p.start_date ? `${fmt(p.start_date, { month: 'short', day: 'numeric' })} – ${fmt(p.end_date)}` : fmt(p.start_date));
const iso = (y, m, day) => `${y}-${String(m + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
const t12 = (t) => { if (!t || !/^\d{1,2}:\d{2}$/.test(t)) return t || ''; const [h, m] = t.split(':').map(Number); return `${((h + 11) % 12) + 1}:${String(m).padStart(2, '0')} ${h < 12 ? 'AM' : 'PM'}`; };
const when = (e) => (e.kind === 'program' ? sessionDates({ start_date: e.date, end_date: e.end_date }) + (e.schedule ? ` · ${e.schedule}` : '') : fmt(e.date, { weekday: 'short', month: 'short', day: 'numeric', year: 'numeric' }) + (e.start_time ? ` · ${t12(e.start_time)}${e.end_time ? ` – ${t12(e.end_time)}` : ''}` : ''));
const KIND = { session: ['Program session', '#B4247E'], program: ['Program', '#3B0A2E'], event: ['Event', '#CBA24B'] };
const img = (u) => (u ? (u.startsWith('/api/') ? mediaSrc(u) : u) : '');

function Seats({ e }) {
  if (e.kind === 'event') return null;
  if (e.full) return <span className="text-[12px] font-semibold text-red-600 bg-red-50 rounded-full px-3 py-1">Full · waitlist</span>;
  if (e.seats_left != null) return <span className="text-[12px] font-semibold text-[#1f7a4d] bg-[#eaf5ee] rounded-full px-3 py-1 flex items-center gap-1"><Users size={12} /> {e.seats_left} spots left</span>;
  return null;
}

function Cta({ e, className = '' }) {
  if (e.kind === 'event') return <Link to="/events" data-testid="session-cta" className={`btn-gold rounded-full px-5 py-2 font-semibold text-[13px] ${className}`}>RSVP on Events</Link>;
  if (e.kind === 'session' && e.full) return <Link to={`/initiatives/${e.slug}`} data-testid="session-cta" className={`rounded-full px-5 py-2 font-semibold text-[13px] border border-[#3B0A2E]/15 text-[#3B0A2E] ${className}`}>Choose another date</Link>;
  return <Link to={e.link} data-testid="session-cta" className={`btn-magenta rounded-full px-5 py-2 font-semibold text-[13px] ${className}`}>{e.full ? 'Join Waitlist' : 'Sign Up'}</Link>;
}

function EntryCard({ e, onOpen }) {
  const [label, color] = KIND[e.kind];
  return (
    <button onClick={onOpen} className="text-left w-full bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden flex flex-col sm:flex-row card-hover" data-testid="session-card">
      {img(e.image_url) && <img loading="lazy" decoding="async" src={img(e.image_url)} alt={e.title} className="sm:w-44 h-36 sm:h-auto object-cover" />}
      <div className="p-5 flex-1 flex flex-col">
        <span className="text-[11px] uppercase tracking-wide font-semibold mb-1" style={{ color }}>{label}{e.category && e.category !== 'Event' ? ` · ${e.category}` : ''}</span>
        <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1" data-testid="session-title">{e.title}</h3>
        <p className="text-[13px] text-[#3B0A2E] font-semibold flex items-center gap-1.5" data-testid="session-dates"><CalendarDays size={14} className="text-[#B4247E]" /> {when(e)}</p>
        {e.location && <p className="text-[12.5px] text-[#241019]/60 flex items-center gap-1.5 mt-1"><MapPin size={13} /> {e.location}</p>}
        <div className="mt-3 flex flex-wrap items-center gap-3"><Seats e={e} /><span className="text-[12.5px] font-semibold text-[#B4247E]">Details →</span></div>
      </div>
    </button>
  );
}

function DetailModal({ e, onClose }) {
  useEffect(() => { const k = (x) => x.key === 'Escape' && onClose(); window.addEventListener('keydown', k); return () => window.removeEventListener('keydown', k); }, [onClose]);
  const [label, color] = KIND[e.kind];
  return (
    <div data-testid="session-detail-modal" className="fixed inset-0 z-[70] bg-[#29061F]/70 backdrop-blur-[12px] flex items-end md:items-center justify-center md:p-6 animate-[fadeIn_.25s_ease]" onClick={onClose}>
      <div onClick={(x) => x.stopPropagation()} className="bg-white w-full md:max-w-xl rounded-t-[28px] md:rounded-[28px] overflow-hidden max-h-[90vh] overflow-y-auto relative animate-[slideUp_.35s_ease]">
        {img(e.image_url) && <img loading="lazy" decoding="async" src={img(e.image_url)} alt={e.title} className="w-full h-52 object-cover" />}
        <button data-testid="session-detail-close" onClick={onClose} className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/90 text-[#3B0A2E] flex items-center justify-center hover:rotate-90 transition-transform duration-300"><X size={20} /></button>
        <div className="p-7">
          <span className="text-[11px] uppercase tracking-[0.2em] font-semibold" style={{ color }}>{label}{e.category && e.category !== 'Event' ? ` · ${e.category}` : ''}</span>
          <h2 data-testid="session-detail-title" className="font-serif text-[28px] text-[#3B0A2E] font-semibold leading-tight mt-1 mb-4">{e.title}</h2>
          <div className="space-y-2 text-[14px] text-[#241019]/80 mb-5">
            <p className="flex items-center gap-2"><CalendarDays size={16} className="text-[#B4247E]" /> {when(e)}</p>
            {e.location && <p className="flex items-center gap-2"><MapPin size={16} className="text-[#B4247E]" /> {e.location}</p>}
            {e.notes && <p className="flex items-center gap-2"><Clock size={16} className="text-[#B4247E]" /> {e.notes}</p>}
          </div>
          {e.summary && <p className="text-[14.5px] leading-relaxed text-[#241019]/70 mb-6 whitespace-pre-line">{e.summary}</p>}
          <div className="flex flex-wrap items-center gap-3">
            <Cta e={e} />
            <Seats e={e} />
            {e.kind !== 'event' && <Link to={`/initiatives/${e.slug}`} className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E]">About this program</Link>}
            {e.gcal_url && <a href={e.gcal_url} target="_blank" rel="noopener noreferrer" data-testid="session-detail-gcal" className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] flex items-center gap-1"><CalendarPlus size={14} /> Google Calendar</a>}
            {e.ics_url && <a href={`${BACKEND_URL}${e.ics_url}`} data-testid="session-detail-ics" className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] flex items-center gap-1"><CalendarPlus size={14} /> Apple / Outlook</a>}
            {e.program_feed && <a href={`${BACKEND_URL}${e.program_feed}`.replace(/^https?:\/\//, 'webcal://')} data-testid="session-detail-feed" className="text-[13px] font-semibold text-[#3B0A2E] hover:text-[#B4247E] flex items-center gap-1"><Link2 size={14} /> Subscribe to all dates</a>}
          </div>
        </div>
      </div>
    </div>
  );
}

function MonthGrid({ items, month, setMonth, onOpen }) {
  const y = month.getFullYear(), m = month.getMonth();
  const days = new Date(y, m + 1, 0).getDate();
  const offset = new Date(y, m, 1).getDay();
  const today = iso(new Date().getFullYear(), new Date().getMonth(), new Date().getDate());
  const on = (day) => items.filter((p) => { const s = iso(y, m, day); return s >= p.date && s <= (p.end_date || p.date); });
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
          return (
            <div key={day} className={`min-h-[64px] md:min-h-[80px] rounded-lg p-1 md:p-1.5 text-left ${list.length ? 'bg-[#fdf9fb]' : ''} ${iso(y, m, day) === today ? 'ring-2 ring-[#B4247E]/40' : 'border border-[#3B0A2E]/5'}`} data-testid="sessions-day">
              <span className="text-[11.5px] font-semibold text-[#3B0A2E]/70">{day}</span>
              {list.slice(0, 2).map((p) => (
                <button key={`${p.kind}-${p.id}`} onClick={() => onOpen(p)} title={p.title} data-testid="sessions-day-event" className="block w-full mt-0.5 truncate text-left text-[10px] md:text-[10.5px] font-semibold text-white rounded px-1 py-0.5 hover:opacity-85 transition-opacity" style={{ background: KIND[p.kind][1] }}>{p.title}</button>
              ))}
              {list.length > 2 && <button onClick={() => onOpen(list[2])} className="text-[10px] text-[#241019]/55">+{list.length - 2} more</button>}
            </div>
          );
        })}
      </div>
      <div className="flex flex-wrap gap-4 mt-4 text-[12px] text-[#241019]/60">{Object.entries(KIND).map(([k, [l, c]]) => <span key={k} className="flex items-center gap-1.5"><span className="w-3 h-3 rounded" style={{ background: c }} /> {l}</span>)}</div>
    </div>
  );
}

function SubscribeBar() {
  const [copied, setCopied] = useState(false);
  const feed = `${BACKEND_URL}/api/sessions.ics`;
  const webcal = feed.replace(/^https?:\/\//, 'webcal://');
  const copy = async () => { try { await navigator.clipboard.writeText(feed); setCopied(true); setTimeout(() => setCopied(false), 2000); } catch (e) { console.error('Copy failed', e); } };
  const btn = 'px-5 py-2.5 rounded-full text-[13px] font-semibold flex items-center gap-1.5 transition-colors';
  return (
    <div className="rounded-2xl p-5 mb-8 flex flex-wrap items-center gap-3 text-white" style={{ background: 'linear-gradient(160deg,#3B0A2E,#4d1240)' }} data-testid="sessions-subscribe">
      <p className="flex-1 min-w-[220px] text-[14px]"><strong className="font-serif text-[17px]">Never miss a session.</strong> <span className="text-[#F7EFE9]/75">Subscribe once and new sessions appear in your calendar automatically.</span></p>
      <a href={`https://calendar.google.com/calendar/r?cid=${encodeURIComponent(webcal)}`} target="_blank" rel="noopener noreferrer" data-testid="sessions-subscribe-google" className={`${btn} btn-gold`}><CalendarPlus size={15} /> Add to Google Calendar</a>
      <a href={webcal} data-testid="sessions-subscribe-apple" className={`${btn} bg-white text-[#3B0A2E] hover:bg-[#F7EFE9]`}><CalendarPlus size={15} /> Apple / Outlook</a>
      <button onClick={copy} data-testid="sessions-subscribe-copy" className={`${btn} text-white border border-white/30 hover:bg-white/10`}>{copied ? <Check size={15} /> : <Link2 size={15} />} {copied ? 'Copied' : 'Copy feed link'}</button>
    </div>
  );
}

export default function Sessions() {
  const [data, setData] = useState(null);
  const [view, setView] = useState(() => (typeof window !== 'undefined' && window.innerWidth < 640 ? 'list' : 'calendar'));
  const [kind, setKind] = useState('all');
  const [cat, setCat] = useState('');
  const [open, setOpen] = useState(null);
  const [month, setMonth] = useState(() => { const t = new Date(); return new Date(t.getFullYear(), t.getMonth(), 1); });
  useEffect(() => {
    api.get('/sessions/calendar').then(({ data: r }) => {
      setData(r);
      const first = r.entries[0];
      const now = new Date();
      if (first && d(first.date) > new Date(now.getFullYear(), now.getMonth() + 1, 0)) setMonth(new Date(d(first.date).getFullYear(), d(first.date).getMonth(), 1));
    }).catch(() => setData({ entries: [], categories: [] }));
  }, []);
  const close = useCallback(() => setOpen(null), []);
  const items = (data?.entries || []).filter((e) => (kind === 'all' || (kind === 'program' ? e.kind !== 'event' : e.kind === 'event')) && (!cat || e.category === cat));
  const chip = (on) => `px-4 py-2 rounded-full text-[13px] font-semibold transition-colors ${on ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12 hover:border-[#B4247E]'}`;
  return (
    <div data-testid="sessions-page">
      <PageHero kicker="Plan ahead" title="Upcoming Sessions & Events" subtitle="See every program session and event in one place, check how many spots are left, and save your place." />
      <section className="py-14 lg:py-20">
        <div className="max-w-6xl mx-auto px-5 lg:px-8">
          <SubscribeBar />
          <div className="flex flex-wrap items-center gap-2 mb-6">
            {[['calendar', 'Calendar', CalendarDays], ['list', 'List', List]].map(([v, l, Icon]) => (
              <button key={v} onClick={() => setView(v)} data-testid={`sessions-view-${v}`} className={`px-5 py-2 rounded-full text-[13.5px] font-semibold flex items-center gap-1.5 transition-colors ${view === v ? 'bg-[#B4247E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12'}`}><Icon size={15} /> {l}</button>
            ))}
            <span className="w-px h-6 bg-[#3B0A2E]/10 mx-2 hidden sm:block" />
            {[['all', 'Everything'], ['program', 'Program sessions'], ['event', 'Events']].map(([k, l]) => <button key={k} data-testid={`sessions-kind-${k}`} onClick={() => setKind(k)} className={chip(kind === k)}>{l}</button>)}
            {data?.categories?.length > 0 && (
              <select data-testid="sessions-category-filter" value={cat} onChange={(e) => setCat(e.target.value)} className="rounded-full border border-[#3B0A2E]/12 bg-white px-4 py-2 text-[13px] font-semibold text-[#3B0A2E]">
                <option value="">All categories</option>{data.categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            )}
          </div>
          {!data ? <Loader2 className="animate-spin text-[#B4247E]" /> : items.length === 0 ? (
            <p className="text-[15px] text-[#241019]/60 py-10" data-testid="sessions-empty">{data.entries.length ? 'Nothing matches these filters.' : 'No upcoming sessions or events are scheduled yet.'} <Link to="/initiatives" className="text-[#B4247E] font-semibold">Browse our programs</Link>.</p>
          ) : view === 'calendar' ? (
            <div className="grid lg:grid-cols-[1.4fr_1fr] gap-6 items-start">
              <MonthGrid items={items} month={month} setMonth={setMonth} onOpen={setOpen} />
              <div className="space-y-4"><p className="eyebrow text-[#B4247E]">Coming up next</p>{items.slice(0, 4).map((e) => <EntryCard key={`${e.kind}-${e.id}`} e={e} onOpen={() => setOpen(e)} />)}</div>
            </div>
          ) : (
            <div className="grid gap-4" data-testid="sessions-list">{items.map((e) => <EntryCard key={`${e.kind}-${e.id}`} e={e} onOpen={() => setOpen(e)} />)}</div>
          )}
        </div>
      </section>
      {open && <DetailModal e={open} onClose={close} />}
    </div>
  );
}
