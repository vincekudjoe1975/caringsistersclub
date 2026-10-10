import React, { useEffect, useMemo, useState } from 'react';
import { Loader2, Scale, ArrowUpDown, Trophy } from 'lucide-react';
import { api } from '../lib/api';

const KIND = { segment: 'Segment', scheduled: 'Scheduled', recurring: 'Recurring', year_in_review: 'Year in Review' };
const money = (n) => (n === null || n === undefined ? '—' : `$${Number(n).toLocaleString('en-US', { maximumFractionDigits: 2 })}`);
const pct = (n) => (n === null || n === undefined ? '—' : `${n}%`);
const COLS = [
  ['sent_at', 'Sent', (r) => (r.sent_at ? new Date(r.sent_at).toLocaleDateString() : '—')],
  ['recipients', 'Recipients', (r) => r.recipients], ['clicks', 'Clicks', (r) => r.clicks], ['click_rate', 'Click rate', (r) => pct(r.click_rate)],
  ['gifts', 'Gifts', (r) => r.gifts], ['raised', 'Raised', (r) => money(r.raised)], ['per_recipient', '$ / recipient', (r) => money(r.per_recipient)],
];
const METRICS = [['recipients', 'Recipients', String], ['clicks', 'Clicks', String], ['click_rate', 'Click rate', pct], ['gifts', 'Gifts', String], ['raised', 'Raised', money], ['per_recipient', '$ per recipient', money]];

function Compare({ rows }) {
  const best = Object.fromEntries(METRICS.map(([k]) => [k, Math.max(...rows.map((r) => r[k] ?? -1))]));
  return (
    <div className="grid gap-4 mt-5" style={{ gridTemplateColumns: `repeat(${Math.min(rows.length, 4)}, minmax(0,1fr))` }} data-testid="appeal-compare-cards">
      {rows.map((r) => (
        <div key={r.id} className="rounded-xl p-4 border border-[#3B0A2E]/10" style={{ background: '#fdf9fb' }} data-testid="appeal-compare-card">
          <span className="text-[10.5px] uppercase tracking-wide font-semibold text-[#B4247E]">{KIND[r.kind] || r.kind}</span>
          <p className="font-semibold text-[#3B0A2E] text-[14px] leading-snug mt-1 mb-3 line-clamp-2">{r.name}</p>
          {METRICS.map(([k, l, f]) => (
            <div key={k} className="flex items-center justify-between py-1 text-[12.5px] border-t border-[#3B0A2E]/6">
              <span className="text-[#241019]/60">{l}</span>
              <span className={`font-semibold flex items-center gap-1 ${r[k] !== null && r[k] === best[k] && best[k] > 0 ? 'text-[#B4247E]' : 'text-[#3B0A2E]'}`}>{r[k] !== null && r[k] === best[k] && best[k] > 0 && <Trophy size={11} />}{f(r[k])}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}

export const AppealComparison = () => {
  const [items, setItems] = useState(null);
  const [sort, setSort] = useState(['sent_at', -1]);
  const [picked, setPicked] = useState([]);
  useEffect(() => { api.get('/admin/reports/appeal-comparison').then(({ data }) => setItems(data.items)).catch(() => setItems([])); }, []);
  const rows = useMemo(() => [...(items || [])].sort((a, b) => ((a[sort[0]] ?? -1) > (b[sort[0]] ?? -1) ? 1 : -1) * sort[1]), [items, sort]);
  const toggle = (id) => setPicked((p) => (p.includes(id) ? p.filter((x) => x !== id) : [...p, id]));
  const chosen = rows.filter((r) => picked.includes(r.id));
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="appeal-comparison">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><Scale size={18} className="text-[#B4247E]" /> Appeal results comparison</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">Every appeal email side by side. Tick two or more to compare them.</p>
      {!items ? <Loader2 className="animate-spin text-[#B4247E]" /> : rows.length === 0 ? <p className="text-[13px] text-[#241019]/55" data-testid="appeal-comparison-empty">No appeal emails sent yet.</p> : (
        <div className="overflow-x-auto"><table className="w-full text-left text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50"><th className="px-2 py-2" /><th className="px-3 py-2">Appeal</th>
            {COLS.map(([k, l]) => <th key={k} className="px-3 py-2"><button onClick={() => setSort([k, sort[0] === k ? -sort[1] : -1])} data-testid={`appeal-sort-${k}`} className="flex items-center gap-1 uppercase">{l}<ArrowUpDown size={11} /></button></th>)}</tr></thead>
          <tbody>{rows.map((r) => (
            <tr key={r.id} className={`border-t border-[#3B0A2E]/8 ${picked.includes(r.id) ? 'bg-[#faf2f7]' : ''}`} data-testid="appeal-row">
              <td className="px-2 py-2.5"><input type="checkbox" checked={picked.includes(r.id)} onChange={() => toggle(r.id)} data-testid="appeal-compare-checkbox" className="accent-[#B4247E]" /></td>
              <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E] max-w-[260px] truncate">{r.name}</p><p className="text-[11px] text-[#241019]/50">{KIND[r.kind] || r.kind}{r.segment ? ` · ${r.segment}` : ''}</p></td>
              {COLS.map(([k, , f]) => <td key={k} className="px-3 py-2.5">{f(r)}</td>)}
            </tr>
          ))}</tbody>
        </table></div>
      )}
      {chosen.length >= 2 && <Compare rows={chosen} />}
      {chosen.length === 1 && <p className="text-[12px] text-[#241019]/55 mt-3">Pick at least one more appeal to compare.</p>}
    </div>
  );
};
