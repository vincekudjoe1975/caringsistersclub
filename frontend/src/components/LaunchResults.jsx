import React, { useEffect, useState } from 'react';
import { Loader2, Megaphone } from 'lucide-react';
import { api } from '../lib/api';

export const LaunchResults = () => {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/admin/reports/launch-results').then(({ data }) => setD(data)).catch(() => setD({ items: [], window_days: 30 })); }, []);
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="launch-results">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><Megaphone size={18} className="text-[#B4247E]" /> Session launch email results</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">A sign-up counts when someone who got the launch email signs up for (or joins the waitlist of) that session within {d?.window_days || 30} days.</p>
      {!d ? <Loader2 className="animate-spin text-[#B4247E]" /> : d.items.length === 0 ? <p className="text-[13px] text-[#241019]/55" data-testid="launch-results-empty">No launch emails sent yet.</p> : (
        <table className="w-full text-left text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50">{['Session', 'Sent', 'Emailed', 'Signed up', 'Conversion'].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>{d.items.map((r) => (
            <tr key={r.id} className="border-t border-[#3B0A2E]/8" data-testid="launch-results-row">
              <td className="px-3 py-2.5 font-semibold text-[#3B0A2E]">{r.title}</td>
              <td className="px-3 py-2.5 text-[#241019]/60">{r.sent_at ? new Date(r.sent_at).toLocaleDateString() : '—'}</td>
              <td className="px-3 py-2.5" data-testid="launch-results-emailed">{r.emailed}</td>
              <td className="px-3 py-2.5" data-testid="launch-results-signed">{r.signed_up}</td>
              <td className="px-3 py-2.5 font-bold text-[#B4247E]" data-testid="launch-results-conversion">{r.conversion === null ? '—' : `${r.conversion}%`}</td>
            </tr>
          ))}</tbody>
        </table>
      )}
    </div>
  );
};
