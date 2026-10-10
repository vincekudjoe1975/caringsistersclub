import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Printer, Share2, EyeOff } from 'lucide-react';
import { TreasurerBody } from '../../../pages/TreasurerReport';

const inputCls = 'rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';

export function AdminTreasurer() {
  const { toast } = useToast();
  const now = new Date();
  const [ym, setYm] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`);
  const [r, setR] = useState(null);
  const [year, month] = ym.split('-').map(Number);
  const load = useCallback(() => api.get('/admin/members/treasurer', { params: { year, month } }).then(({ data }) => setR(data)), [year, month]);
  useEffect(() => { load(); }, [load]);
  const share = async () => { await api.post('/admin/members/treasurer/share', { year, month }); toast({ title: 'Report shared', description: 'Members can now see it in the Minutes tab.' }); load(); };
  const unshare = async () => { await api.delete('/admin/members/treasurer/share', { params: { year, month } }); toast({ title: 'Report hidden from members' }); load(); };
  return (
    <div data-testid="admin-treasurer">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-5 flex flex-wrap items-center gap-3">
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold mr-auto">Treasurer's report</p>
        <input data-testid="treasurer-month" type="month" value={ym} onChange={(e) => e.target.value && setYm(e.target.value)} className={inputCls} />
        <a data-testid="treasurer-open-print" href={`/treasurer-report?year=${year}&month=${month}`} target="_blank" rel="noreferrer" className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Printer size={14} /> Printable page</a>
        {r?.shared
          ? <button data-testid="treasurer-unshare-btn" onClick={unshare} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><EyeOff size={14} /> Hide from members</button>
          : <button data-testid="treasurer-share-btn" onClick={share} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Share2 size={14} /> Share with members</button>}
      </div>
      {r?.shared && <p data-testid="treasurer-shared-note" className="text-[12.5px] text-green-700 mb-3">Shared with members on {new Date(r.shared.shared_at).toLocaleDateString()}. Sharing again updates their copy with today's figures.</p>}
      {r && <div className="bg-white rounded-2xl p-6 md:p-8 border border-[#3B0A2E]/8"><TreasurerBody r={r} /></div>}
      {r?.shared && <button data-testid="treasurer-reshare-btn" onClick={share} className="mt-3 text-[12.5px] font-semibold text-[#B4247E]">Update shared copy</button>}
    </div>
  );
}
