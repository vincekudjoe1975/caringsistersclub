import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, History, Archive, Lightbulb } from 'lucide-react';
import { ResponsiveContainer, LineChart, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from 'recharts';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const fmt = (iso) => (iso ? new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—');

function SeasonRow({ s, testid }) {
  return (
    <tr className="border-t border-[#3B0A2E]/8" data-testid={testid}>
      <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{s.label}</td>
      <td className="px-3 py-2.5 text-[#241019]/65">{fmt(s.start)} – {s.kind === 'current' ? 'now' : fmt(s.end)}</td>
      <td className="px-3 py-2.5">{s.capacity ? `${s.taken}/${s.capacity}` : `${s.taken} (no limit)`}</td>
      <td className="px-3 py-2.5">{s.signups}</td>
      <td className="px-3 py-2.5">{s.waitlist}</td>
      <td className="px-3 py-2.5 font-semibold text-[#B4247E]" data-testid={`${testid}-filled`}>{s.days_to_fill === null ? 'Not filled' : `Filled in ${s.days_to_fill} day${s.days_to_fill === 1 ? '' : 's'}`}</td>
    </tr>
  );
}

function HistoryBody({ h, onClose }) {
  const chart = [...h.monthly.map((m) => ({ label: m.label, 'Seats filled': m.taken, Waitlist: m.waitlist, 'Sign-ups': m.signups })),
    { label: 'Now', 'Seats filled': h.current.taken, Waitlist: h.current.waitlist, 'Sign-ups': h.current.signups }];
  return (
    <>
      {h.suggestion && <p className="rounded-xl px-4 py-3 mb-4 text-[13px] text-[#5c4a1f] flex items-center gap-2" style={{ background: '#fdf3e1' }} data-testid="history-seat-suggestion"><Lightbulb size={15} className="text-[#8a6a2c] shrink-0" />{h.suggestion.suggested ? <span><strong>Next session: {h.suggestion.suggested} seats suggested.</strong> {h.suggestion.why}</span> : h.suggestion.why}</p>}
      <div className="h-56 mb-5" data-testid="history-chart">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chart} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
            <CartesianGrid stroke="#f2e6ee" /><XAxis dataKey="label" fontSize={11} /><YAxis allowDecimals={false} fontSize={11} /><Tooltip /><Legend wrapperStyle={{ fontSize: 12 }} />
            <Line type="monotone" dataKey="Seats filled" stroke="#B4247E" strokeWidth={2} /><Line type="monotone" dataKey="Waitlist" stroke="#CBA24B" strokeWidth={2} /><Line type="monotone" dataKey="Sign-ups" stroke="#3B0A2E" strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="overflow-x-auto"><table className="w-full text-left text-[13px]"><thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-3 py-2">Season</th><th className="px-3 py-2">Dates</th><th className="px-3 py-2">Seats</th><th className="px-3 py-2">Sign-ups</th><th className="px-3 py-2">Waitlist</th><th className="px-3 py-2">Fill speed</th></tr></thead>
        <tbody><SeasonRow s={h.current} testid="history-current" />{[...h.seasons].reverse().map((s) => <SeasonRow key={s.id} s={s} testid="history-season" />)}</tbody></table></div>
      <button onClick={onClose} data-testid="close-season-btn" className="mt-4 text-[12.5px] font-semibold px-4 py-2 rounded-full text-white bg-[#3B0A2E] flex items-center gap-1.5"><Archive size={13} /> Close season</button>
      <p className="text-[11.5px] text-[#241019]/50 mt-2">Closing a season saves a snapshot, archives current enrollments (seats reopen for the next season) and offers freed seats to the waitlist. Monthly snapshots are saved automatically.</p>
    </>
  );
}

export const ForecastHistory = () => {
  const { toast } = useToast();
  const [programs, setPrograms] = useState([]);
  const [pid, setPid] = useState('');
  const [h, setH] = useState(null);
  useEffect(() => { api.get('/admin/programs').then(({ data }) => { setPrograms(data.items); if (data.items[0]) setPid(data.items[0].id); }).catch(() => {}); }, []);
  const load = useCallback(() => { if (pid) { setH(null); api.get(`/admin/programs/${pid}/history`).then(({ data }) => setH(data)).catch(() => setH(undefined)); } }, [pid]);
  useEffect(() => { load(); }, [load]);
  const close = async () => {
    const label = window.prompt('Name this season (e.g. "Spring 2026")', '');
    if (label === null) return;
    try { const { data } = await api.post(`/admin/programs/${pid}/close-season`, { label }); toast({ title: `Season "${data.snapshot.label}" saved`, description: `${data.archived} enrollment(s) archived.` }); load(); }
    catch (err) { toast({ title: 'Could not close season', description: err?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="forecast-history">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><History size={18} className="text-[#B4247E]" /> Forecast history</h3>
        <select value={pid} onChange={(e) => setPid(e.target.value)} data-testid="history-program-select" className="text-[13px] rounded-full px-3 py-1.5 border border-[#3B0A2E]/15 max-w-xs">
          {programs.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </div>
      {h === null ? <Loader2 className="animate-spin text-[#B4247E]" /> : h === undefined ? <p className="text-[13px] text-red-600">Could not load history.</p> : <HistoryBody h={h} onClose={close} />}
    </div>
  );
};
