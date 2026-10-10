import React, { useEffect, useState } from 'react';
import { Timer, Lightbulb } from 'lucide-react';
import { api } from '../lib/api';

const hrs = (h) => (h === null || h === undefined ? '—' : h < 1 ? `${Math.round(h * 60)} min` : `${h} h`);

export const WaitlistSpeed = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/reports/waitlist-speed').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d) return null;
  const s = d.summary;
  const stat = (label, v, id) => <div className="rounded-xl px-4 py-3" style={{ background: '#faf2f7' }}><p className="text-[11px] uppercase tracking-wide text-[#241019]/55 font-semibold">{label}</p><p className="font-serif text-[22px] font-bold text-[#3B0A2E]" data-testid={id}>{v}</p></div>;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="waitlist-speed">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><Timer size={18} className="text-[#B4247E]" /> Waitlist speed</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">How quickly freed seats get claimed from the waitlist. Claim rate counts claimed vs expired offers.</p>
      {d.items.length === 0 ? <p className="text-[13px] text-[#241019]/55" data-testid="waitlist-speed-empty">No waitlist offers yet.</p> : (
        <>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-5">
            {stat('Offers sent', s.offers, 'ws-offers')}{stat('Median claim time', hrs(s.median_hours), 'ws-median')}{stat('Claim rate', s.claim_rate === null ? '—' : `${s.claim_rate}%`, 'ws-claim-rate')}
            {stat('Expired', s.expired, 'ws-expired')}{stat('Auto moved in', s.auto_moved, 'ws-auto')}
          </div>
          <table className="w-full text-left text-[13px]">
            <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50">{['Program', 'Offers', 'Claimed', 'Expired', 'Open', 'Auto moved', 'Claim rate', 'Median time'].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
            <tbody>{d.items.map((r) => (
              <tr key={r.program_id || r.title} className="border-t border-[#3B0A2E]/8" data-testid="waitlist-speed-row">
                <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E]">{r.title} <span className="text-[11px] font-normal text-[#241019]/50">· {r.offer_hours}h window</span></p>
                  {r.tip && <p className="text-[11.5px] text-[#8a6a2c] flex items-center gap-1 mt-0.5" data-testid="waitlist-speed-tip"><Lightbulb size={12} /> {r.tip}</p>}</td><td className="px-3 py-2.5">{r.offers}</td><td className="px-3 py-2.5">{r.claimed}</td>
                <td className="px-3 py-2.5">{r.expired}</td><td className="px-3 py-2.5">{r.pending}</td><td className="px-3 py-2.5">{r.auto_moved}</td>
                <td className="px-3 py-2.5 font-bold text-[#B4247E]">{r.claim_rate === null ? '—' : `${r.claim_rate}%`}</td><td className="px-3 py-2.5">{hrs(r.median_hours)}</td>
              </tr>
            ))}</tbody>
          </table>
        </>
      )}
    </div>
  );
};
