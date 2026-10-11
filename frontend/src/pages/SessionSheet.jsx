import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../lib/api';
import { Loader2, Printer } from 'lucide-react';

const BLANK_ROWS = 8;

export default function SessionSheet() {
  const { sid } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get(`/admin/sessions/${sid}/roster`).then(({ data }) => setD(data)).catch((e) => setErr([401, 403].includes(e?.response?.status) ? 'auth' : 'Could not load this session.')); }, [sid]);
  if (err === 'auth') return <div className="min-h-screen flex items-center justify-center"><p data-testid="sheet-auth">Staff sign-in required. <Link to="/login" className="text-[#B4247E] font-semibold">Sign in</Link></p></div>;
  if (err) return <div className="min-h-screen flex items-center justify-center"><p data-testid="sheet-error">{err}</p></div>;
  if (!d) return <div className="min-h-screen flex items-center justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div>;
  const cell = 'border border-[#3B0A2E]/25 px-3 py-2.5 text-[13px]';
  return (
    <div className="bg-white min-h-screen p-8 print:p-0 max-w-5xl mx-auto" data-testid="session-sheet-page">
      <div className="flex justify-end mb-4 print:hidden">
        <button data-testid="sheet-print-btn" onClick={() => window.print()} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Printer size={14} /> Print sign-in sheet</button>
      </div>
      <div className="flex items-end justify-between border-b-2 border-[#3B0A2E] pb-3 mb-5">
        <div><p className="text-[11px] uppercase tracking-[0.25em] text-[#B4247E] font-semibold">Caring Sisters Club · Sign-in sheet</p>
          <h1 data-testid="sheet-title" className="font-serif text-[26px] text-[#3B0A2E] font-semibold leading-tight">{d.program}</h1>
          <p className="text-[13px] text-[#241019]/70">{d.label}</p></div>
        <p className="text-[12px] text-[#241019]/60">{d.items.length} signed up</p>
      </div>
      <table className="w-full border-collapse" data-testid="sheet-table">
        <thead><tr className="bg-[#F7EFE9]" style={{ WebkitPrintColorAdjust: 'exact', printColorAdjust: 'exact' }}>
          {['#', 'Name', 'Phone', 'Email', 'Signature'].map((h) => <th key={h} className={`${cell} text-left text-[11.5px] uppercase tracking-wide text-[#3B0A2E]`}>{h}</th>)}
        </tr></thead>
        <tbody>
          {d.items.map((r, i) => (
            <tr key={r.id} data-testid={`sheet-row-${r.id}`}>
              <td className={`${cell} w-10 text-[#241019]/50`}>{i + 1}</td><td className={`${cell} font-semibold`}>{r.name}</td>
              <td className={cell}>{r.phone}</td><td className={cell}>{r.email}</td><td className={`${cell} w-[30%]`} />
            </tr>
          ))}
          {Array.from({ length: BLANK_ROWS }).map((_, i) => (
            <tr key={`b${i}`} data-testid="sheet-blank-row"><td className={`${cell} text-[#241019]/40`}>{d.items.length + i + 1}</td><td className={`${cell} h-10`} /><td className={cell} /><td className={cell} /><td className={cell} /></tr>
          ))}
        </tbody>
      </table>
      <p className="text-[11px] text-[#241019]/50 mt-4">Walk-ins: please print your name, phone and email in the blank rows.</p>
    </div>
  );
}
