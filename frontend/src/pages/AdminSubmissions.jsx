import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, Trash2, Mail, MailOpen, HandHeart, Users, MessageSquare, CalendarCheck, Heart, Layers, AlarmClock, Send } from 'lucide-react';

const TYPES = [
  { key: 'volunteer', label: 'Volunteers', icon: HandHeart },
  { key: 'member', label: 'Memberships', icon: Users },
  { key: 'contact', label: 'Contact', icon: MessageSquare },
  { key: 'rsvp', label: 'Event RSVPs', icon: CalendarCheck },
  { key: 'program_signup', label: 'Program Sign-Ups', icon: Layers },
  { key: 'donation', label: 'Donations', icon: Heart },
];

const STAGES = [['new', 'New', '#eef1f5', '#53657d'], ['contacted', 'Contacted', '#fdf3e1', '#8a6a2c'], ['enrolled', 'Enrolled', '#e9f3e6', '#3c7a2f'], ['not_fit', 'Not a fit', '#f5e9ec', '#9b3b4f']];

function StageSelect({ it, onChange }) {
  const cur = STAGES.find((s) => s[0] === (it.stage || 'new'));
  const change = async (e) => {
    const stage = e.target.value;
    try { await api.put(`/admin/submissions/${it.id}/stage`, { stage }); onChange(stage); }
    catch (err) { console.error('Stage update failed', err); }
  };
  return (
    <select value={cur[0]} onChange={change} data-testid="signup-stage-select" className="text-[12px] font-semibold rounded-full px-3 py-1 border-0 cursor-pointer"
      style={{ background: cur[2], color: cur[3] }}>
      {STAGES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
    </select>
  );
}

const isOverdue = (it) => it.type === 'program_signup' && (it.stage || 'new') === 'new' && Date.now() - new Date(it.created_at).getTime() >= 7 * 864e5;

function OverdueBar({ count, only, setOnly }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  const send = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/signups/send-reminders'); toast({ title: data.sent ? 'Reminder sent to staff' : 'Nothing to remind', description: `${data.overdue} sign-up(s) overdue` }); }
    catch (err) { toast({ title: 'Reminder failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  return (
    <div className="bg-white rounded-2xl px-5 py-3.5 border border-[#3B0A2E]/8 mb-4 flex flex-wrap items-center justify-between gap-3" data-testid="overdue-bar">
      <p className="text-[13.5px] text-[#3B0A2E] flex items-center gap-2"><AlarmClock size={16} className="text-[#9b3b4f]" /> <strong data-testid="overdue-count">{count}</strong> sign-up{count === 1 ? '' : 's'} still "New" after 7+ days. Staff get a daily reminder email.</p>
      <div className="flex items-center gap-2">
        <label className="text-[12.5px] font-semibold text-[#3B0A2E] flex items-center gap-1.5"><input type="checkbox" checked={only} onChange={(e) => setOnly(e.target.checked)} data-testid="overdue-only-checkbox" className="accent-[#B4247E]" /> Overdue only</label>
        <button onClick={send} disabled={busy || !count} data-testid="send-enroll-reminder-btn" className="text-[12.5px] font-semibold px-4 py-1.5 rounded-full text-white bg-[#3B0A2E] flex items-center gap-1.5 disabled:opacity-50">{busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Send reminder now</button>
      </div>
    </div>
  );
}

function fieldLabel(k) {
  return k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, ' ');
}

export default function AdminSubmissions() {
  const { toast } = useToast();
  const [type, setType] = useState('volunteer');
  const [items, setItems] = useState([]);
  const [counts, setCounts] = useState({});
  const [loading, setLoading] = useState(false);
  const [overdueOnly, setOverdueOnly] = useState(false);
  const shown = overdueOnly && type === 'program_signup' ? items.filter(isOverdue) : items;

  const loadCounts = useCallback(async () => {
    try {
      const { data } = await api.get('/submissions/counts');
      setCounts(data);
    } catch (e) { console.error('AdminSubmissions: failed to load counts', e); }
  }, []);

  const load = useCallback(async (t) => {
    setLoading(true);
    try {
      const { data } = await api.get(`/submissions?type=${t}`);
      setItems(data);
    } catch (e) {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadCounts(); }, [loadCounts]);
  useEffect(() => { load(type); }, [type, load]);

  const markRead = async (id) => {
    try {
      await api.patch(`/submissions/${id}/read`);
      setItems((prev) => prev.map((i) => (i.id === id ? { ...i, read: true } : i)));
      loadCounts();
    } catch (e) { console.error('AdminSubmissions: failed to mark read', e); }
  };

  const remove = async (id) => {
    try {
      await api.delete(`/submissions/${id}`);
      setItems((prev) => prev.filter((i) => i.id !== id));
      loadCounts();
      toast({ title: 'Deleted' });
    } catch (e) {
      toast({ title: 'Delete failed', variant: 'destructive' });
    }
  };

  return (
    <div className="grid lg:grid-cols-[260px_1fr] gap-8 items-start">
      {/* Type list */}
      <div className="bg-white rounded-2xl p-3 border border-[#3B0A2E]/8">
        {TYPES.map((t) => {
          const Icon = t.icon;
          const c = counts[t.key] || { total: 0, unread: 0 };
          const active = type === t.key;
          return (
            <button key={t.key} onClick={() => setType(t.key)}
              className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-[14px] font-semibold mb-1 transition-all ${active ? 'text-white' : 'text-[#3B0A2E] hover:bg-[#f2e6ee]'}`}
              style={active ? { background: '#B4247E' } : {}}>
              <span className="flex items-center gap-2.5"><Icon size={17} /> {t.label}</span>
              <span className={`text-[11px] px-2 py-0.5 rounded-full ${active ? 'bg-white/25' : 'bg-[#f2e6ee] text-[#B4247E]'}`}>
                {c.unread > 0 ? `${c.unread} new` : c.total}
              </span>
              {c.overdue > 0 && <span className="text-[10.5px] px-2 py-0.5 rounded-full bg-[#f5e9ec] text-[#9b3b4f] ml-1" data-testid="overdue-sidebar-badge">{c.overdue} overdue</span>}
            </button>
          );
        })}
      </div>

      {/* Items */}
      <div>
        {type === 'program_signup' && <OverdueBar count={counts.program_signup?.overdue || 0} only={overdueOnly} setOnly={setOverdueOnly} />}
        {loading ? (
          <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
        ) : shown.length === 0 ? (
          <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8">
            <p className="text-[#241019]/50">No submissions yet.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {shown.map((it) => (
              <div key={it.id} className={`bg-white rounded-2xl p-6 border ${it.read ? 'border-[#3B0A2E]/8' : 'border-[#B4247E]/40'}`}>
                <div className="flex items-start justify-between gap-4 mb-3">
                  <div className="flex items-center gap-2">
                    {!it.read && <span className="w-2 h-2 rounded-full" style={{ background: '#B4247E' }} />}
                    <p className="font-serif text-[18px] text-[#3B0A2E] font-semibold">
                      {it.data?.name || it.data?.email || 'Submission'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    {isOverdue(it) && <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#f5e9ec] text-[#9b3b4f] flex items-center gap-1" data-testid="signup-overdue-badge"><AlarmClock size={12} /> Overdue</span>}
                    {it.waitlist && <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#fdf3e1] text-[#8a6a2c]" data-testid="signup-waitlist-badge">Waitlist</span>}
                    {it.came_back && <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#faf2f7] text-[#B4247E]" data-testid="signup-came-back-badge">Came back</span>}
                    {it.from_launch && <span className="text-[11px] font-semibold px-2.5 py-1 rounded-full bg-[#e9f3e6] text-[#3c7a2f]" data-testid="signup-from-launch-badge">From launch email</span>}
                    {it.type === 'program_signup' && <StageSelect it={it} onChange={(stage) => { setItems((prev) => prev.map((i) => (i.id === it.id ? { ...i, stage, read: true } : i))); loadCounts(); }} />}
                    <span className="text-[11.5px] text-[#241019]/45">{new Date(it.created_at).toLocaleString()}</span>
                    <button onClick={() => markRead(it.id)} title={it.read ? 'Read' : 'Mark read'} className="text-[#B4247E] hover:text-[#D14FA0] p-1.5">
                      {it.read ? <MailOpen size={16} /> : <Mail size={16} />}
                    </button>
                    <button onClick={() => remove(it.id)} className="text-red-500 hover:text-red-700 p-1.5"><Trash2 size={16} /></button>
                  </div>
                </div>
                <div className="grid sm:grid-cols-2 gap-x-6 gap-y-2">
                  {Object.entries(it.data || {}).map(([k, v]) => (
                    v !== '' && v != null && k !== 'program_slug' && (
                      <div key={k} className="text-[13.5px]">
                        <span className="text-[#241019]/45">{fieldLabel(k)}: </span>
                        <span className="text-[#3B0A2E]">{String(v)}</span>
                      </div>
                    )
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
