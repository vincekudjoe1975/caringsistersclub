import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, TrendingUp, TrendingDown, Minus, Download, Clock3, Check, X, BarChart3 } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

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

export default function AdminReports() {
  return (
    <div data-testid="admin-reports">
      <h2 className="font-serif text-[24px] text-[#3B0A2E] font-semibold mb-5">Reports</h2>
      <StoryRequestResults />
      <SignupReport />
      <HoursReview />
    </div>
  );
}
