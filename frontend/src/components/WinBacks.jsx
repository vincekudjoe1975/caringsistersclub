import React, { useEffect, useState } from 'react';
import { HeartHandshake, ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../lib/api';

const money = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 2 })}`;
const day = (iso) => (iso ? new Date(iso).toLocaleDateString() : '—');

function Stat({ label, value, testid, accent }) {
  return (
    <div className="rounded-xl px-4 py-3" style={{ background: '#faf2f7' }}>
      <p className="text-[11px] uppercase tracking-wide text-[#241019]/55 font-semibold">{label}</p>
      <p className="font-serif text-[24px] font-bold" style={{ color: accent || '#3B0A2E' }} data-testid={testid}>{value}</p>
    </div>
  );
}

function Row({ r }) {
  const status = r.returned ? ['Returned', '#e9f3e6', '#3c7a2f'] : r.thanked ? ['Note sent', '#f2e6ee', '#B4247E'] : ['No note yet', '#eef1f5', '#53657d'];
  return (
    <tr className="border-t border-[#3B0A2E]/8 text-[13px]" data-testid="winback-row">
      <td className="px-4 py-3"><p className="font-semibold text-[#3B0A2E]">{r.name}</p><p className="text-[12px] text-[#241019]/55">{r.email}</p></td>
      <td className="px-4 py-3">{money(r.amount)}/mo</td>
      <td className="px-4 py-3 text-[#241019]/65">{day(r.created_at)}</td>
      <td className="px-4 py-3 text-[#241019]/65">{day(r.thanked_at)}</td>
      <td className="px-4 py-3"><span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full" style={{ background: status[1], color: status[2] }} data-testid="winback-status">{status[0]}</span></td>
      <td className="px-4 py-3 text-right font-semibold text-[#3c7a2f]">{r.recovered ? money(r.recovered) : ''}</td>
    </tr>
  );
}

export const WinBacks = () => {
  const [data, setData] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { api.get('/admin/winbacks').then(({ data: d }) => setData(d)).catch((e) => console.error('WinBacks: load failed', e)); }, []);
  if (!data) return null;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-5 mb-5" data-testid="winbacks-card">
      <div className="flex items-center justify-between gap-3 mb-4">
        <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2"><HeartHandshake size={18} className="text-[#B4247E]" /> Win-Backs</h3>
        {data.items.length > 0 && (
          <button onClick={() => setOpen(!open)} data-testid="winbacks-toggle-btn" className="text-[12.5px] font-semibold text-[#B4247E] flex items-center gap-1">
            {open ? 'Hide' : 'Show'} donors {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        )}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <Stat label="Cancellations" value={data.cancellations} testid="winbacks-cancellations" />
        <Stat label="Notes sent" value={data.notes_sent} testid="winbacks-notes" />
        <Stat label="Returned" value={data.returned} testid="winbacks-returned" accent="#3c7a2f" />
        <Stat label="Win-back rate" value={`${data.rate}%`} testid="winbacks-rate" accent="#B4247E" />
        <Stat label="Recovered" value={money(data.recovered)} testid="winbacks-recovered" accent="#3c7a2f" />
      </div>
      {data.items.length === 0 && <p className="text-[12.5px] text-[#241019]/55 mt-3">No monthly cancellations yet. When one happens you'll get an email with a one-click thank-you note.</p>}
      {open && (
        <div className="overflow-x-auto mt-4">
          <table className="w-full text-left">
            <thead><tr className="text-[11.5px] uppercase tracking-wide text-[#241019]/50">
              <th className="px-4 py-2 font-semibold">Donor</th><th className="px-4 py-2 font-semibold">Gift</th><th className="px-4 py-2 font-semibold">Cancelled</th>
              <th className="px-4 py-2 font-semibold">Note sent</th><th className="px-4 py-2 font-semibold">Status</th><th className="px-4 py-2 font-semibold text-right">Recovered</th>
            </tr></thead>
            <tbody>{data.items.map((r) => <Row key={`${r.email}-${r.created_at}`} r={r} />)}</tbody>
          </table>
        </div>
      )}
    </div>
  );
};
