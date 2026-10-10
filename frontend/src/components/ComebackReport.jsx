import React, { useEffect, useState } from 'react';
import { HeartHandshake } from 'lucide-react';
import { api } from '../lib/api';

export const ComebackReport = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/reports/comebacks').then(({ data }) => setD(data)).catch(() => {}); }, []);
  if (!d) return null;
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="comeback-report">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><HeartHandshake size={18} className="text-[#B4247E]" /> "We missed you" comebacks</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">A comeback is a no-show who signs up for any session of the same program within {d.window_days} days of the email.</p>
      {d.items.length === 0 ? <p className="text-[13px] text-[#241019]/55" data-testid="comeback-empty">No "we missed you" emails sent yet.</p> : (
        <>
          <p className="text-[14px] text-[#3B0A2E] mb-3" data-testid="comeback-summary"><strong>{d.summary.comebacks}</strong> of {d.summary.sent} came back ({d.summary.rate ?? 0}%)</p>
          <table className="w-full text-left text-[13px]">
            <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50">{['Program', 'Emails sent', 'Came back', 'Comeback rate'].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
            <tbody>{d.items.map((r) => (
              <tr key={r.program_id} className="border-t border-[#3B0A2E]/8" data-testid="comeback-row">
                <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{r.title}</td><td className="px-3 py-2.5">{r.sent}</td><td className="px-3 py-2.5">{r.comebacks}</td>
                <td className="px-3 py-2.5 font-bold text-[#B4247E]">{r.rate === null ? '—' : `${r.rate}%`}</td>
              </tr>
            ))}</tbody>
          </table>
        </>
      )}
    </div>
  );
};
