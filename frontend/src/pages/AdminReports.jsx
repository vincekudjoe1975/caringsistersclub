import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, TrendingUp, TrendingDown, Minus, Download, Clock3, Check, X, BarChart3, Sparkles, ExternalLink, UploadCloud, Eye, Send } from 'lucide-react';
import { api, BACKEND_URL, mediaSrc } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { ProgramForecast } from '../components/ProgramForecast';
import { ForecastHistory } from '../components/ForecastHistory';
import { AppealComparison } from '../components/AppealComparison';
import { TemplateInsights } from '../components/TemplateInsights';

const monthLabel = (k) => new Date(`${k}-01T00:00:00`).toLocaleDateString('en-US', { month: 'short', year: '2-digit' });
const csvCell = (v) => { let t = String(v ?? ''); if (/^[=+\-@\t\r]/.test(t)) t = `'${t}`; return `"${t.replace(/"/g, '""')}"`; };

export const Trend = ({ t }) => (t === 'up' ? <TrendingUp size={16} className="text-[#3c7a2f]" /> : t === 'down' ? <TrendingDown size={16} className="text-[#B4247E]" /> : <Minus size={16} className="text-[#241019]/35" />);

export function useSignupReport(months = 6) {
  const [data, setData] = useState(null);
  useEffect(() => { api.get(`/admin/reports/program-signups?months=${months}`).then(({ data: d }) => setData(d)).catch(() => setData({ months: [], rows: [], totals: [] })); }, [months]);
  return data;
}

function SignupReport() {
  const data = useSignupReport(6);
  if (!data) return <div className="flex justify-center py-10"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const exportCsv = () => {
    const lines = [['Program', ...data.months, 'Total', 'Contacted %', 'Enrolled %'], ...data.rows.map((r) => [r.program, ...r.counts, r.total, r.contacted_pct, r.enrolled_pct]), ['All programs', ...data.totals, data.totals.reduce((a, b) => a + b, 0)]];
    const blob = new Blob([lines.map((l) => l.map(csvCell).join(',')).join('\n')], { type: 'text/csv;charset=utf-8;' });
    const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'program-signups.csv'; a.click(); URL.revokeObjectURL(a.href);
  };
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="signup-report">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><BarChart3 size={18} className="text-[#B4247E]" /> Program Interest: sign-ups per month</h3>
        <button onClick={exportCsv} data-testid="signup-report-export-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><Download size={14} /> CSV</button>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-left text-[13px]">
          <thead><tr className="text-[11.5px] uppercase tracking-wide text-[#241019]/50">
            <th className="px-3 py-2 font-semibold">Program</th>{data.months.map((m) => <th key={m} className="px-3 py-2 font-semibold text-right">{monthLabel(m)}</th>)}
            <th className="px-3 py-2 font-semibold text-right">Total</th><th className="px-3 py-2 font-semibold text-center">Trend</th>
            <th className="px-3 py-2 font-semibold text-right">Contacted</th><th className="px-3 py-2 font-semibold text-right">Enrolled</th>
          </tr></thead>
          <tbody>
            {data.rows.map((r) => (
              <tr key={r.program} className="border-t border-[#3B0A2E]/8" data-testid="signup-report-row">
                <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{r.program}</td>
                {r.counts.map((c, i) => <td key={i} className={`px-3 py-2.5 text-right ${c ? 'text-[#3B0A2E]' : 'text-[#241019]/30'}`}>{c}</td>)}
                <td className="px-3 py-2.5 text-right font-bold text-[#B4247E]">{r.total}</td>
                <td className="px-3 py-2.5"><span className="flex justify-center" data-testid="signup-report-trend"><Trend t={r.trend} /></span></td>
                <td className="px-3 py-2.5 text-right" data-testid="signup-report-contacted">{r.total ? `${r.contacted_pct}%` : '—'}</td>
                <td className="px-3 py-2.5 text-right font-semibold text-[#3c7a2f]" data-testid="signup-report-enrolled">{r.total ? `${r.enrolled_pct}%` : '—'}</td>
              </tr>
            ))}
            <tr className="border-t-2 border-[#3B0A2E]/15 font-semibold"><td className="px-3 py-2.5">All programs</td>{data.totals.map((c, i) => <td key={i} className="px-3 py-2.5 text-right">{c}</td>)}<td className="px-3 py-2.5 text-right">{data.totals.reduce((a, b) => a + b, 0)}</td><td /><td /><td /></tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}

function StoryRequestResults() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/reports/story-requests').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d) return null;
  const cell = (label, v, id, color) => (
    <div className="rounded-xl px-4 py-3" style={{ background: '#faf2f7' }}>
      <p className="text-[11px] uppercase tracking-wide text-[#241019]/55 font-semibold">{label}</p>
      <p className="font-serif text-[24px] font-bold" style={{ color: color || '#3B0A2E' }} data-testid={id}>{v}</p>
    </div>
  );
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="story-request-results">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-1">Story Request Results</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">Invites emailed 60 days after a program sign-up, and how many led to a submitted story.</p>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {cell('Invites sent', d.invites, 'story-req-invites')}
        {cell('Stories submitted', d.submitted, 'story-req-submitted', '#B4247E')}
        {cell('Response rate', `${d.rate}%`, 'story-req-rate', '#B4247E')}
        {cell('Approved & featured', d.approved, 'story-req-approved', '#3c7a2f')}
      </div>
    </div>
  );
}

function HoursReview() {
  const [items, setItems] = useState(null);
  const [tab, setTab] = useState('pending');
  const { toast } = useToast();
  const load = useCallback(() => api.get('/admin/volunteer-hours').then(({ data }) => setItems(data.items || [])).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);
  const act = async (h, action) => {
    try { await api.post(`/admin/volunteer-hours/${h.id}/${action}`); toast({ title: action === 'approve' ? 'Hours approved' : 'Entry declined' }); load(); }
    catch (err) { toast({ title: 'Action failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  if (!items) return null;
  const approved = items.filter((h) => h.status === 'approved').reduce((s, h) => s + h.hours, 0);
  const shown = items.filter((h) => (tab === 'pending' ? h.status === 'pending' : h.status !== 'pending'));
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6" data-testid="hours-review">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Clock3 size={18} className="text-[#B4247E]" /> Volunteer Hours <span className="text-[13px] font-sans font-normal text-[#241019]/55" data-testid="hours-approved-total">({approved.toFixed(1)} approved hours)</span></h3>
        <BadgeWallSetting />
        <div className="inline-flex gap-1 p-1 rounded-full bg-[#faf2f7]">
          {[['pending', `Pending (${items.filter((h) => h.status === 'pending').length})`], ['reviewed', 'Reviewed']].map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} data-testid={`hours-tab-${k}`} className={`px-4 py-1.5 rounded-full text-[12.5px] font-semibold ${tab === k ? 'text-white' : 'text-[#3B0A2E]'}`} style={tab === k ? { background: '#3B0A2E' } : {}}>{l}</button>
          ))}
        </div>
      </div>
      {shown.length === 0 ? <p className="text-[13px] text-[#241019]/55 text-center py-6" data-testid="hours-empty">{tab === 'pending' ? 'No hours waiting for review.' : 'Nothing reviewed yet.'}</p> : (
        <table className="w-full text-left text-[13px]"><tbody>{shown.map((h) => (
          <tr key={h.id} className="border-t border-[#3B0A2E]/8" data-testid="hours-row">
            <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E]">{h.name}</p><p className="text-[11.5px] text-[#241019]/55">{h.email}</p></td>
            <td className="px-3 py-2.5">{h.program}</td>
            <td className="px-3 py-2.5 text-[#241019]/65">{h.date}</td>
            <td className="px-3 py-2.5 font-bold text-[#3B0A2E]">{h.hours}h</td>
            <td className="px-3 py-2.5 text-[#241019]/65 max-w-[220px] truncate" title={h.note}>{h.note}</td>
            <td className="px-3 py-2.5 text-right whitespace-nowrap">
              {h.status === 'pending' ? <>
                <button onClick={() => act(h, 'approve')} data-testid="hours-approve-btn" className="p-1.5 text-[#3c7a2f]"><Check size={16} /></button>
                <button onClick={() => act(h, 'reject')} data-testid="hours-reject-btn" className="p-1.5 text-red-500"><X size={16} /></button>
              </> : <span className="text-[11px] font-semibold capitalize" style={{ color: h.status === 'approved' ? '#3c7a2f' : '#53657d' }} data-testid="hours-status">{h.status}</span>}
            </td>
          </tr>
        ))}</tbody></table>
      )}
    </div>
  );
}

function BadgeWallSetting() {
  const { toast } = useToast();
  const [mode, setMode] = useState(null);
  useEffect(() => { api.get('/admin/badge-wall').then(({ data }) => setMode(data.mode)).catch(() => {}); }, []);
  const change = async (e) => {
    const m = e.target.value; setMode(m);
    try { await api.put('/admin/badge-wall', { mode: m }); toast({ title: 'Badge wall updated' }); } catch { toast({ title: 'Save failed', variant: 'destructive' }); }
  };
  if (!mode) return null;
  return (
    <label className="text-[12.5px] text-[#3B0A2E] font-semibold flex items-center gap-2" data-testid="badge-wall-setting">Badge wall shows:
      <select value={mode} onChange={change} data-testid="badge-wall-mode-select" className="rounded-full px-3 py-1.5 border border-[#3B0A2E]/15 font-normal">
        <option value="optin">Only leaderboard opt-ins</option><option value="all">Everyone who earned a badge</option>
      </select>
    </label>
  );
}

function YirShareImage({ year, d, onSaved }) {
  const { toast } = useToast();
  const [busy, setBusy] = useState(false);
  const save = async (image_url) => {
    try { const { data } = await api.put(`/admin/year-in-review/${year}`, { image_url }); onSaved({ image_url: data.image_url }); toast({ title: image_url ? 'Share image updated' : 'Using the auto-generated card' }); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file); fd.append('category', 'share'); fd.append('title', `Year in Review ${year} share image`);
    setBusy(true);
    try { const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); await save(data.url); }
    catch (err) { toast({ title: 'Upload failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const src = d.image_url ? mediaSrc(d.image_url) : `${BACKEND_URL}/api/share/year-in-review/${year}/card.png?v=${d.donations_total}-${d.volunteer_hours}-${d.signups}`;
  return (
    <div className="mt-5 grid md:grid-cols-[320px_1fr] gap-5 items-start" data-testid="yir-share-image">
      <img src={src} alt="Share preview" className="w-full rounded-xl border border-[#3B0A2E]/10" data-testid="yir-share-image-preview" />
      <div>
        <p className="text-[13.5px] font-semibold text-[#3B0A2E] mb-1">Social share image</p>
        <p className="text-[12.5px] text-[#241019]/60 mb-3">{d.image_url ? 'Using your uploaded image.' : 'Auto-generated from this year\'s numbers; it updates as the data changes.'} Shown when the page is shared on Facebook, X, LinkedIn or WhatsApp.</p>
        <div className="flex flex-wrap gap-2">
          <label className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#B4247E] flex items-center gap-1.5 cursor-pointer" style={{ border: '1px solid rgba(180,36,126,0.3)' }}>
            {busy ? <Loader2 size={13} className="animate-spin" /> : <UploadCloud size={13} />} {d.image_url ? 'Replace image' : 'Upload my own'}
            <input type="file" accept="image/png,image/jpeg,image/webp" className="hidden" data-testid="yir-share-image-upload" onChange={(e) => upload(e.target.files?.[0])} />
          </label>
          {d.image_url && <button onClick={() => save('')} data-testid="yir-share-image-reset" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#3B0A2E]" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>Use auto card</button>}
        </div>
      </div>
    </div>
  );
}

function AskAmount({ year, d, onSaved }) {
  const { toast } = useToast();
  const [v, setV] = useState(d.ask_amount || 50);
  const save = async () => {
    try { const { data } = await api.put(`/admin/year-in-review/${year}`, { ask_amount: Number(v) }); onSaved({ ask_amount: data.ask_amount }); toast({ title: `Suggested gift set to $${data.ask_amount}` }); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div className="mt-3 flex flex-wrap items-center gap-2 text-[12.5px] text-[#3B0A2E]" data-testid="yir-ask-amount">
      <span className="font-semibold">"Help us do it again" suggested gift: $</span>
      <input type="number" min="1" value={v} onChange={(e) => setV(e.target.value)} data-testid="yir-ask-amount-input" className="w-24 rounded-full px-3 py-1.5 border border-[#3B0A2E]/15" />
      <button onClick={save} disabled={Number(v) === d.ask_amount} data-testid="yir-ask-amount-save" className="font-semibold px-4 py-1.5 rounded-full text-white bg-[#3B0A2E] disabled:opacity-40">Save</button>
      <span className="text-[#241019]/55">Past donors see their own last gift amount in the email.</span>
    </div>
  );
}

function YirEmail({ year, d, onSaved }) {
  const { toast } = useToast();
  const [info, setInfo] = useState(null);
  const [testTo, setTestTo] = useState('');
  const [busy, setBusy] = useState('');
  const [preview, setPreview] = useState(false);
  const load = useCallback(() => api.get(`/admin/year-in-review/${year}/email`).then(({ data }) => setInfo(data)).catch(() => setInfo(null)), [year]);
  useEffect(() => { load(); }, [load]);
  const run = async (key, fn, ok) => {
    setBusy(key);
    try { await fn(); toast({ title: ok }); load(); }
    catch (err) {
      if (err?.response?.status === 409 && key === 'send' && window.confirm(`${err.response.data.detail}`)) { await run('send', () => api.post(`/admin/year-in-review/${year}/email/send`, { force: true }), ok); return; }
      toast({ title: 'Something went wrong', description: err?.response?.data?.detail, variant: 'destructive' });
    } finally { setBusy(''); }
  };
  const toggleAuto = (e) => api.put(`/admin/year-in-review/${year}`, { autosend: e.target.checked }).then(({ data }) => onSaved({ autosend: data.autosend }));
  if (!info) return null;
  const last = info.history?.[0];
  return (
    <div className="mt-5 pt-5 border-t border-[#3B0A2E]/8" data-testid="yir-email">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[13.5px] text-[#3B0A2E]"><strong>Email the Year in Review</strong> to <strong data-testid="yir-email-recipients">{info.recipients}</strong> donors &amp; volunteers from {year} (deduplicated).</p>
        <div className="flex flex-wrap items-center gap-2">
          <button onClick={() => setPreview(!preview)} data-testid="yir-email-preview-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#3B0A2E] flex items-center gap-1.5" style={{ border: '1px solid rgba(59,10,46,0.15)' }}><Eye size={13} /> {preview ? 'Hide preview' : 'Preview'}</button>
          <input value={testTo} onChange={(e) => setTestTo(e.target.value)} placeholder="test@email.com" data-testid="yir-email-test-input" className="text-[12.5px] rounded-full px-3 py-2 border border-[#3B0A2E]/15 w-44" />
          <button disabled={!testTo || !!busy} onClick={() => run('test', () => api.post(`/admin/year-in-review/${year}/email/test`, { email: testTo }), 'Test email sent')} data-testid="yir-email-test-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#B4247E] disabled:opacity-50" style={{ border: '1px solid rgba(180,36,126,0.3)' }}>{busy === 'test' ? 'Sending…' : 'Send test'}</button>
          <button disabled={!d.public || !info.recipients || !!busy} title={d.public ? '' : 'Publish the page first'} onClick={() => window.confirm(`Email the ${year} Year in Review to ${info.recipients} people?`) && run('send', () => api.post(`/admin/year-in-review/${year}/email/send`, { force: false }), 'Year in Review email is sending')} data-testid="yir-email-send-btn" className="btn-magenta text-[12.5px] font-semibold px-4 py-2 rounded-full flex items-center gap-1.5 disabled:opacity-50"><Send size={13} /> {busy === 'send' ? 'Queuing…' : 'Send to all'}</button>
        </div>
      </div>
      <AskAmount year={year} d={d} onSaved={onSaved} />
      <label className="mt-3 flex items-center gap-2 text-[12.5px] text-[#3B0A2E] font-semibold"><input type="checkbox" checked={!!d.autosend} onChange={toggleAuto} data-testid="yir-autosend-checkbox" className="accent-[#B4247E]" /> Send automatically when a year's page is published (once per year)</label>
      {last && <p className="text-[12px] text-[#241019]/55 mt-2" data-testid="yir-email-last">Last send: {new Date(last.started_at).toLocaleString()} · {last.status === 'done' ? `${last.sent} sent${last.failed ? `, ${last.failed} failed` : ''}` : `sending to ${last.recipients}…`} ({last.trigger})</p>}
      {!d.public && <p className="text-[12px] text-[#9b3b4f] mt-2">Publish the page before sending so the email link works.</p>}
      {preview && <iframe title="Year in Review email preview" srcDoc={info.html} data-testid="yir-email-preview" className="w-full h-[560px] mt-4 rounded-xl border border-[#3B0A2E]/10 bg-white" />}
    </div>
  );
}

function YirResults({ year }) {
  const [r, setR] = useState(null);
  useEffect(() => { api.get(`/admin/year-in-review/${year}/results`).then(({ data }) => setR(data)).catch(() => setR(null)); }, [year]);
  if (!r) return null;
  const row = (key, label) => {
    const x = r[key];
    return (
      <tr className="border-t border-[#3B0A2E]/8" data-testid={`yir-results-${key}`}>
        <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{label}</td>
        <td className="px-3 py-2.5" data-testid={`yir-results-${key}-clicks`}>{x.clicks}</td>
        <td className="px-3 py-2.5">{x.checkouts}</td>
        <td className="px-3 py-2.5" data-testid={`yir-results-${key}-gifts`}>{x.gifts}</td>
        <td className="px-3 py-2.5 font-bold text-[#B4247E]" data-testid={`yir-results-${key}-raised`}>${x.raised.toLocaleString()}</td>
        <td className="px-3 py-2.5">{x.conversion === null ? '—' : `${x.conversion}%`}</td>
      </tr>
    );
  };
  return (
    <div className="mt-5 pt-5 border-t border-[#3B0A2E]/8" data-testid="yir-results">
      <p className="text-[13.5px] font-semibold text-[#3B0A2E] mb-2">"Help us do it again" results</p>
      <table className="w-full text-left text-[13px]"><thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-3 py-2">Source</th><th className="px-3 py-2">Clicks</th><th className="px-3 py-2">Checkouts</th><th className="px-3 py-2">Gifts</th><th className="px-3 py-2">Raised</th><th className="px-3 py-2">Click→gift</th></tr></thead>
        <tbody>{row('email', 'Email button')}{row('page', 'Page button')}</tbody></table>
    </div>
  );
}

function YearInReviewAdmin() {
  const now = new Date().getFullYear();
  const [year, setYear] = useState(now);
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const { toast } = useToast();
  useEffect(() => { setD(null); api.get(`/admin/year-in-review/${year}`).then(({ data }) => setD(data)).catch(() => setD({})); }, [year]);
  const merge = (patch) => setD((cur) => ({ ...cur, ...patch }));
  const toggle = async () => {
    setBusy(true);
    try { const { data } = await api.put(`/admin/year-in-review/${year}`, { public: !d.public }); merge({ public: data.public }); toast({ title: data.public ? 'Year in Review is now public' : 'Year in Review hidden', description: data.email_queued ? 'The Year in Review email is being sent automatically.' : undefined }); }
    catch (err) { toast({ title: 'Update failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const stat = (l, v, id) => <div className="rounded-xl px-4 py-3" style={{ background: '#faf2f7' }}><p className="text-[11px] uppercase tracking-wide text-[#241019]/55 font-semibold">{l}</p><p className="font-serif text-[22px] font-bold text-[#3B0A2E]" data-testid={id}>{v}</p></div>;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="yir-admin">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Sparkles size={18} className="text-[#B4247E]" /> Year in Review</h3>
        <div className="flex items-center gap-2">
          <select value={year} onChange={(e) => setYear(Number(e.target.value))} data-testid="yir-year-select" className="text-[13px] rounded-full px-3 py-1.5 border border-[#3B0A2E]/15">
            {[0, 1, 2, 3].map((i) => <option key={i} value={now - i}>{now - i}</option>)}
          </select>
          {d?.year && <button onClick={toggle} disabled={busy} data-testid="yir-publish-toggle" className={`text-[12.5px] font-semibold px-4 py-2 rounded-full ${d.public ? 'text-[#3c7a2f] bg-[#e9f3e6]' : 'text-white bg-[#3B0A2E]'}`}>{d.public ? 'Public · Hide page' : 'Publish page'}</button>}
          {d?.public && <a href={`/year-in-review/${year}`} target="_blank" rel="noreferrer" data-testid="yir-view-link" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-[#B4247E] flex items-center gap-1" style={{ border: '1px solid rgba(180,36,126,0.3)' }}><ExternalLink size={13} /> View</a>}
        </div>
      </div>
      {!d ? <Loader2 className="animate-spin text-[#B4247E]" /> : d.year ? (
        <>
          <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
            {stat('Raised', `$${Math.round(d.donations_total).toLocaleString()}`, 'yir-admin-raised')}{stat('Donors', d.donors, 'yir-admin-donors')}
            {stat('Vol. hours', d.volunteer_hours, 'yir-admin-hours')}{stat('Volunteers', d.volunteers, 'yir-admin-volunteers')}
            {stat('Sign-ups', d.signups, 'yir-admin-signups')}{stat('Stories', d.stories, 'yir-admin-stories')}
          </div>
          <YirShareImage year={year} d={d} onSaved={merge} />
          <YirEmail year={year} d={d} onSaved={merge} />
          <YirResults year={year} />
        </>
      ) : <p className="text-[13px] text-red-600">Could not load this year.</p>}
    </div>
  );
}

export default function AdminReports() {
  return (
    <div data-testid="admin-reports">
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-5">Reports</h2>
      <YearInReviewAdmin />
      <ProgramForecast />
      <ForecastHistory />
      <AppealComparison />
      <TemplateInsights />
      <StoryRequestResults />
      <SignupReport />
      <HoursReview />
    </div>
  );
}
