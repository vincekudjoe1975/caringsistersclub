import React, { useEffect, useState } from 'react';
import { Loader2, FileText, Trophy } from 'lucide-react';
import { api } from '../lib/api';

const money = (n) => (n === null || n === undefined ? '—' : `$${Number(n).toLocaleString('en-US', { maximumFractionDigits: 2 })}`);

export const TemplateInsights = () => {
  const [items, setItems] = useState(null);
  useEffect(() => { api.get('/admin/reports/template-insights').then(({ data }) => setItems(data.items)).catch(() => setItems([])); }, []);
  return (
    <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 p-6 mb-6" data-testid="template-insights">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold flex items-center gap-2 mb-1"><FileText size={18} className="text-[#B4247E]" /> Appeal template insights</h3>
      <p className="text-[12.5px] text-[#241019]/55 mb-4">Which saved templates raise the most per recipient. Older appeals are matched to templates by subject line.</p>
      {!items ? <Loader2 className="animate-spin text-[#B4247E]" /> : items.length === 0 ? <p className="text-[13px] text-[#241019]/55" data-testid="template-insights-empty">No saved templates yet. Save one from Donors → Email segment.</p> : (
        <div className="overflow-x-auto"><table className="w-full text-left text-[13px]">
          <thead><tr className="text-[11px] uppercase tracking-wide text-[#241019]/50">{['Template', 'Times used', 'Recipients', 'Click rate', 'Gifts', 'Raised', '$ / recipient'].map((h) => <th key={h} className="px-3 py-2">{h}</th>)}</tr></thead>
          <tbody>{items.map((r) => (
            <tr key={r.id} className={`border-t border-[#3B0A2E]/8 ${r.top ? 'bg-[#fdf9ef]' : ''}`} data-testid="template-row">
              <td className="px-3 py-2.5"><p className="font-semibold text-[#3B0A2E] flex items-center gap-2">{r.name}{r.top && <span className="inline-flex items-center gap-1 text-[10.5px] font-bold px-2 py-0.5 rounded-full bg-[#3B0A2E] text-[#CBA24B]" data-testid="template-top-tag"><Trophy size={11} /> Top performer</span>}</p>
                <p className="text-[11px] text-[#241019]/50 truncate max-w-[280px]">{r.subject}{r.matched ? ` · ${r.matched} matched by subject` : ''}</p></td>
              <td className="px-3 py-2.5" data-testid="template-uses">{r.uses}</td>
              <td className="px-3 py-2.5">{r.recipients}</td>
              <td className="px-3 py-2.5">{r.click_rate === null ? '—' : `${r.click_rate}%`}</td>
              <td className="px-3 py-2.5">{r.gifts}</td>
              <td className="px-3 py-2.5 font-semibold text-[#B4247E]">{money(r.raised)}</td>
              <td className="px-3 py-2.5 font-semibold" data-testid="template-per-recipient">{money(r.per_recipient)}</td>
            </tr>
          ))}</tbody>
        </table></div>
      )}
    </div>
  );
};
