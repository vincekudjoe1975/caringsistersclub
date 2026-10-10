import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, Check, X, MessageSquareQuote, Mail, Send, Eye } from 'lucide-react';
import { api, mediaSrc } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { resetHomeContentCache } from '../lib/useHomeContent';

function StoryCard({ st, programs, onDone }) {
  const [target, setTarget] = useState(st.program_id || 'home');
  const [quote, setQuote] = useState(st.quote);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  const act = async (kind) => {
    setBusy(true);
    try {
      if (kind === 'approve') {
        const { data } = await api.post(`/admin/stories/${st.id}/approve`, { target, quote });
        resetHomeContentCache();
        toast({ title: 'Story featured', description: `Now showing on ${data.featured_on}.` });
      } else {
        await api.post(`/admin/stories/${st.id}/reject`);
        toast({ title: 'Story declined' });
      }
      onDone();
    } catch (err) {
      toast({ title: 'Action failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally { setBusy(false); }
  };
  const pending = st.status === 'pending';
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-5" data-testid="story-submission">
      <div className="flex items-start gap-3">
        {st.photo_url ? <img src={mediaSrc(st.photo_url)} alt="" className="w-12 h-12 rounded-full object-cover" /> : <span className="w-12 h-12 rounded-full bg-[#faf2f7]" />}
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-[#3B0A2E]">{st.name} <span className="font-normal text-[12px] text-[#241019]/55">{st.email}{st.role && ` · ${st.role}`}</span></p>
          <p className="text-[11.5px] text-[#241019]/50">{new Date(st.created_at).toLocaleString()}{st.program_title && ` · submitted on ${st.program_title}`}</p>
        </div>
        <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full capitalize" data-testid="story-status"
          style={{ background: pending ? '#fdf3e1' : st.status === 'approved' ? '#e9f3e6' : '#eef1f5', color: pending ? '#8a6a2c' : st.status === 'approved' ? '#3c7a2f' : '#53657d' }}>
          {st.status}{st.featured_on && ` · ${st.featured_on}`}
        </span>
      </div>
      {pending ? (
        <>
          <textarea rows={3} value={quote} onChange={(e) => setQuote(e.target.value)} data-testid="story-edit-quote"
            className="w-full mt-3 rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] italic focus:outline-none focus:border-[#B4247E]" />
          <div className="flex flex-wrap items-center gap-2 mt-3">
            <span className="text-[12.5px] text-[#3B0A2E] font-semibold">Feature on</span>
            <select value={target} onChange={(e) => setTarget(e.target.value)} data-testid="story-target-select" className="rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13px] bg-white">
              <option value="home">Home page</option>
              {programs.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
            </select>
            <button onClick={() => act('approve')} disabled={busy} data-testid="story-approve-btn" className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold flex items-center gap-1.5"><Check size={14} /> Approve & Feature</button>
            <button onClick={() => act('reject')} disabled={busy} data-testid="story-reject-btn" className="rounded-full px-4 py-2 text-[12.5px] font-semibold text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><X size={14} /> Decline</button>
          </div>
        </>
      ) : <p className="mt-3 text-[13.5px] italic text-[#241019]/75">&ldquo;{st.quote}&rdquo;</p>}
    </div>
  );
}

function ImpactHistory() {
  const [items, setItems] = useState([]);
  useEffect(() => { api.get('/admin/impact-email/history').then(({ data }) => setItems(data.items || [])).catch(() => {}); }, []);
  if (!items.length) return null;
  return (
    <div className="mt-5 overflow-x-auto" data-testid="impact-history">
      <p className="text-[12.5px] font-semibold text-[#3B0A2E] mb-2">Engagement <span className="font-normal text-[#241019]/50">(opens are approximate; some email apps block tracking images)</span></p>
      <table className="w-full text-left text-[13px]">
        <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-3 py-2">Sent</th><th className="px-3 py-2 text-right">Delivered</th><th className="px-3 py-2 text-right">Opened</th><th className="px-3 py-2 text-right">Clicked</th></tr></thead>
        <tbody>{items.map((s) => (
          <tr key={s.id} className="border-t border-[#3B0A2E]/8" data-testid="impact-history-row">
            <td className="px-3 py-2">{new Date(s.sent_at).toLocaleDateString()} <span className="text-[11px] text-[#241019]/45 capitalize">({s.trigger})</span></td>
            <td className="px-3 py-2 text-right">{s.sent}</td>
            <td className="px-3 py-2 text-right" data-testid="impact-history-opens">{s.opens} <span className="text-[#241019]/45">({s.open_rate}%)</span></td>
            <td className="px-3 py-2 text-right font-semibold text-[#B4247E]" data-testid="impact-history-clicks">{s.clicks} <span className="text-[#241019]/45 font-normal">({s.click_rate}%)</span></td>
          </tr>
        ))}</tbody>
      </table>
    </div>
  );
}

function StoryRequestToggle() {
  const [on, setOn] = useState(null);
  const { toast } = useToast();
  useEffect(() => { api.get('/admin/settings').then(({ data }) => setOn(data.story_requests_enabled !== false)).catch(() => {}); }, []);
  if (on === null) return null;
  const flip = async () => {
    try { await api.put('/admin/settings', { story_requests_enabled: !on }); setOn(!on); toast({ title: !on ? 'Story requests turned on' : 'Story requests turned off' }); }
    catch { toast({ title: 'Could not update', variant: 'destructive' }); }
  };
  return (
    <label className="mt-5 pt-4 border-t border-[#3B0A2E]/8 flex items-start gap-3 cursor-pointer" data-testid="story-request-toggle">
      <input type="checkbox" checked={on} onChange={flip} className="accent-[#B4247E] w-4 h-4 mt-0.5" data-testid="story-request-checkbox" />
      <span className="text-[13px] text-[#3B0A2E]"><strong>Automatic story requests</strong><br /><span className="text-[#241019]/60">Email each program sign-up once, 60 days after they join, inviting them to share their story.</span></span>
    </label>
  );
}

function ImpactEmail() {
  const [info, setInfo] = useState(null);
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState('');
  const { toast } = useToast();
  const load = useCallback(() => api.get('/admin/impact-email/preview').then(({ data }) => setInfo(data)).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  const send = async (kind) => {
    if (kind === 'send' && !window.confirm(`Send this month's impact update to ${info.recipients} monthly donor(s) now?`)) return;
    setBusy(kind);
    try {
      const { data } = await api.post(`/admin/impact-email/${kind}`);
      toast(data.skipped ? { title: 'Nothing to send', description: data.skipped } : { title: kind === 'test' ? 'Test copy sent to you' : 'Impact update sent', description: `${data.sent} of ${data.recipients} delivered` });
      load();
    } catch (err) { toast({ title: 'Send failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' }); }
    finally { setBusy(''); }
  };
  if (!info) return null;
  const empty = !info.photos && !info.stories;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="impact-email-panel">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Mail size={18} className="text-[#B4247E]" /> Monthly Impact Email</h3>
          <p className="text-[12.5px] text-[#241019]/60 mt-0.5" data-testid="impact-email-summary">
            Sends automatically on the 1st of each month to <strong>{info.recipients}</strong> monthly donor(s). This month: <strong>{info.photos}</strong> new photo(s), <strong>{info.stories}</strong> new story(ies).
            {info.last_sent && ` Last sent ${new Date(info.last_sent.sent_at).toLocaleDateString()} (${info.last_sent.sent} delivered).`}
          </p>
          {empty && <p className="text-[12.5px] text-[#8a6a2c] mt-1">Add program photos or feature a story this month — the update is skipped when there's nothing new.</p>}
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShow(!show)} data-testid="impact-preview-btn" className="rounded-full px-4 py-2 text-[12.5px] font-semibold text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><Eye size={14} /> {show ? 'Hide' : 'Preview'}</button>
          <button onClick={() => send('test')} disabled={!!busy || empty} data-testid="impact-test-btn" className="rounded-full px-4 py-2 text-[12.5px] font-semibold text-[#3B0A2E] disabled:opacity-40" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>{busy === 'test' ? 'Sending…' : 'Send me a test'}</button>
          <button onClick={() => send('send')} disabled={!!busy || empty || !info.recipients} data-testid="impact-send-btn" className="btn-magenta rounded-full px-4 py-2 text-[12.5px] font-semibold flex items-center gap-1.5 disabled:opacity-40"><Send size={13} /> {busy === 'send' ? 'Sending…' : 'Send now'}</button>
        </div>
      </div>
      {show && <iframe title="Impact email preview" srcDoc={info.html} sandbox="" className="w-full h-[560px] mt-4 rounded-xl border border-[#3B0A2E]/10" data-testid="impact-preview-frame" />}
      <ImpactHistory />
      <StoryRequestToggle />
    </div>
  );
}

export default function AdminStories() {
  const [items, setItems] = useState(null);
  const [programs, setPrograms] = useState([]);
  const [tab, setTab] = useState('pending');
  const load = useCallback(async () => {
    const [s, p] = await Promise.all([api.get('/admin/stories'), api.get('/admin/programs')]);
    setItems(s.data.items || []); setPrograms(p.data.items || []);
  }, []);
  useEffect(() => { load().catch(() => setItems([])); }, [load]);
  const shown = (items || []).filter((s) => (tab === 'pending' ? s.status === 'pending' : s.status !== 'pending'));
  const pendingCount = (items || []).filter((s) => s.status === 'pending').length;
  return (
    <div data-testid="admin-stories">
      <ImpactEmail />
      <div className="flex items-end justify-between mb-4">
        <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold flex items-center gap-2"><MessageSquareQuote size={22} className="text-[#B4247E]" /> Member Stories</h2>
        <div className="inline-flex gap-1 p-1 rounded-full bg-white border border-[#3B0A2E]/8">
          {[['pending', `Pending (${pendingCount})`], ['reviewed', 'Reviewed']].map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} data-testid={`stories-tab-${k}`} className={`px-4 py-1.5 rounded-full text-[13px] font-semibold ${tab === k ? 'text-white' : 'text-[#3B0A2E]'}`} style={tab === k ? { background: '#3B0A2E' } : {}}>{l}</button>
          ))}
        </div>
      </div>
      {items === null ? <div className="flex justify-center py-12"><Loader2 className="animate-spin text-[#B4247E]" /></div>
        : shown.length === 0 ? <div className="bg-white rounded-2xl p-10 text-center text-[13.5px] text-[#241019]/55 border border-[#3B0A2E]/8" data-testid="stories-empty">{tab === 'pending' ? 'No stories waiting for review.' : 'No reviewed stories yet.'}</div>
          : <div className="space-y-3">{shown.map((st) => <StoryCard key={st.id} st={st} programs={programs} onDone={load} />)}</div>}
    </div>
  );
}
