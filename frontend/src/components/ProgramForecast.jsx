import React, { useEffect, useState, useCallback } from 'react';
import { Loader2, Gauge, AlertTriangle, Send, Copy } from 'lucide-react';
import { CloneProgramDialog } from './CloneProgram';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

function Spark({ weeks }) {
  const max = Math.max(1, ...weeks);
  return (
    <div className="flex items-end gap-1 h-8" title={`Sign-ups per week (oldest → newest): ${weeks.join(', ')}`} data-testid="forecast-weekly">
      {weeks.map((w, i) => <div key={i} className="w-3 rounded-sm" style={{ height: `${Math.max(8, (w / max) * 100)}%`, background: i === weeks.length - 1 ? '#B4247E' : '#e3c7d8' }} />)}
    </div>
  );
}

function AlertSettings({ s, onChange }) {
  const sel = 'text-[12.5px] rounded-full px-3 py-1.5 border border-[#3B0A2E]/15';
  return (
    <div className="flex flex-wrap items-center gap-3 text-[12.5px] text-[#3B0A2E] mb-4" data-testid="forecast-settings">
      <span className="font-semibold">Waitlist join alerts:</span>
      <select value={s.wl_alert_mode} onChange={(e) => onChange({ wl_alert_mode: e.target.value })} data-testid="wl-alert-mode-select" className={sel}>
        <option value="instant">Instant email for every join</option>
        <option value="digest">One daily digest</option>
        <option value="threshold">Instant, only once the line reaches…</option>
      </select>
      {s.wl_alert_mode === 'threshold' && <input type="number" min="1" value={s.wl_alert_threshold} onChange={(e) => onChange({ wl_alert_threshold: Math.max(1, parseInt(e.target.value || '1', 10)) })} data-testid="wl-alert-threshold-input" className={`${sel} w-20`} />}
      <label className="flex items-center gap-1.5 font-semibold ml-2"><input type="checkbox" checked={s.forecast_weekly} onChange={(e) => onChange({ forecast_weekly: e.target.checked })} data-testid="forecast-weekly-checkbox" className="accent-[#B4247E]" /> Weekly forecast email (Mondays)</label>
    </div>
  );
}

function Row({ r, onClone }) {
  return (
    <tr className="border-t border-[#3B0A2E]/8" data-testid="forecast-row">
      <td className="px-3 py-3"><p className="font-semibold text-[#3B0A2E]">{r.title}</p>
        {r.flag && <span className="inline-flex items-center gap-1 mt-1 text-[11px] font-semibold px-2 py-0.5 rounded-full bg-[#f5e9ec] text-[#9b3b4f]" data-testid="forecast-flag"><AlertTriangle size={11} /> Needs another session · {r.reason}</span>}</td>
      <td className="px-3 py-3 min-w-[130px]">{r.capacity ? (<><div className="h-2 rounded-full bg-[#f2e6ee] overflow-hidden"><div className="h-full rounded-full bg-[#B4247E]" style={{ width: `${Math.min(100, r.fill_pct)}%` }} /></div><p className="text-[11.5px] text-[#241019]/60 mt-1" data-testid="forecast-fill">{r.taken}/{r.capacity} · {r.fill_pct}%</p></>) : <span className="text-[12px] text-[#241019]/45">No seat limit</span>}</td>
      <td className="px-3 py-3"><Spark weeks={r.weekly} /><p className="text-[11px] text-[#241019]/55 mt-1">{r.rate}/wk</p></td>
      <td className="px-3 py-3 text-[12.5px]" data-testid="forecast-days">{r.days_to_fill === null ? '—' : r.days_to_fill === 0 ? 'Full' : `~${r.days_to_fill} days`}</td>
      <td className="px-3 py-3 font-semibold text-[#3B0A2E]" data-testid="forecast-waitlist">{r.waitlist}</td>
      <td className="px-3 py-3 text-right">{r.flag && <button onClick={() => onClone(r)} data-testid="forecast-clone-btn" className="text-[12px] font-semibold px-3 py-1.5 rounded-full text-[#B4247E] whitespace-nowrap inline-flex items-center gap-1" style={{ border: '1px solid rgba(180,36,126,0.3)' }}><Copy size={12} /> Clone session</button>}</td>
    </tr>
  );
}

export const ProgramForecast = () => {
  const { toast } = useToast();
  const [d, setD] = useState(null);
  const [busy, setBusy] = useState(false);
  const [clone, setClone] = useState(null);
  const load = useCallback(() => api.get('/admin/reports/program-forecast').then(({ data }) => setD(data)).catch(() => setD({ items: [], settings: null })), []);
  useEffect(() => { load(); }, [load]);
  const update = async (patch) => {
    const next = { ...d.settings, ...patch };
    setD({ ...d, settings: next });
    try { await api.put('/admin/reports/forecast-settings', next); toast({ title: 'Alert settings saved' }); }
    catch (err) { toast({ title: 'Save failed', description: err?.response?.data?.detail, variant: 'destructive' }); load(); }
  };
  const send = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/reports/program-forecast/send'); toast({ title: data.sent ? 'Forecast emailed to staff' : 'No programs flagged right now' }); }
    catch (err) { toast({ title: 'Send failed', description: err?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const flagged = d?.items?.filter((r) => r.flag).length || 0;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="program-forecast">
      {clone && <CloneProgramDialog program={clone} onClose={() => setClone(null)} onDone={load} />}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Gauge size={18} className="text-[#B4247E]" /> Program fill forecast {flagged > 0 && <span className="text-[11.5px] font-sans font-semibold px-2.5 py-0.5 rounded-full bg-[#f5e9ec] text-[#9b3b4f]" data-testid="forecast-flag-count">{flagged} flagged</span>}</h3>
        <button onClick={send} disabled={busy} data-testid="forecast-send-btn" className="text-[12.5px] font-semibold px-4 py-2 rounded-full text-white bg-[#3B0A2E] flex items-center gap-1.5 disabled:opacity-50">{busy ? <Loader2 size={13} className="animate-spin" /> : <Send size={13} />} Email forecast now</button>
      </div>
      {!d ? <Loader2 className="animate-spin text-[#B4247E]" /> : (
        <>
          {d.settings && <AlertSettings s={d.settings} onChange={update} />}
          {d.items.length === 0 ? <p className="text-[13px] text-[#241019]/55">No published programs yet.</p> : (
            <div className="overflow-x-auto"><table className="w-full text-left text-[13px]"><thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-3 py-2">Program</th><th className="px-3 py-2">Seats filled</th><th className="px-3 py-2">Last 4 weeks</th><th className="px-3 py-2">Days to fill</th><th className="px-3 py-2">Waitlist</th><th /></tr></thead>
              <tbody>{d.items.map((r) => <Row key={r.id} r={r} onClone={setClone} />)}</tbody></table></div>
          )}
          <p className="text-[11.5px] text-[#241019]/50 mt-3">Flagged when the waitlist is 25%+ of capacity or the program is projected to fill within 14 days at the current sign-up pace.</p>
        </>
      )}
    </div>
  );
};
