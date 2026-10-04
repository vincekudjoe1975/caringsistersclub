import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { Loader2, DollarSign, Repeat, Gift, TrendingUp } from 'lucide-react';

export default function AdminDonations() {
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (f) => {
    setLoading(true);
    try {
      const q = f === 'all' ? '' : `?frequency=${f === 'one-time' ? 'one-time' : 'monthly'}`;
      const res = await api.get(`/admin/donations${q}`);
      setData(res.data);
    } catch (e) {
      console.error('AdminDonations: failed to load', e);
      setData({ items: [], summary: {} });
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(filter); }, [filter, load]);

  const s = data?.summary || {};
  const fmt = (n) => `$${Number(n || 0).toLocaleString('en-US', { maximumFractionDigits: 0 })}`;

  const cards = [
    { label: 'Total Raised', value: fmt(s.total_raised), icon: TrendingUp },
    { label: 'Total Gifts', value: s.count ?? 0, icon: Gift },
    { label: 'Active Monthly Donors', value: s.active_recurring ?? 0, icon: Repeat },
    { label: 'Expected / Month', value: fmt(s.monthly_revenue), icon: DollarSign },
  ];

  return (
    <div>
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {cards.map((c) => {
          const Icon = c.icon;
          return (
            <div key={c.label} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
              <span className="w-10 h-10 rounded-xl flex items-center justify-center mb-3" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                <Icon size={18} className="text-white" />
              </span>
              <p className="font-serif text-[26px] text-[#3B0A2E] font-bold leading-none">{c.value}</p>
              <p className="text-[#241019]/55 text-[12.5px] mt-1.5">{c.label}</p>
            </div>
          );
        })}
      </div>

      <div className="flex gap-2 mb-5">
        {[{ k: 'all', l: 'All' }, { k: 'one-time', l: 'One-Time' }, { k: 'monthly', l: 'Monthly' }].map((f) => (
          <button key={f.k} onClick={() => setFilter(f.k)}
            className={`px-4 py-2 rounded-full text-[13.5px] font-semibold transition-all ${filter === f.k ? 'text-white' : 'text-[#3B0A2E] bg-white'}`}
            style={filter === f.k ? { background: '#B4247E' } : { border: '1px solid rgba(59,10,46,0.1)' }}>
            {f.l}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>
      ) : (data?.items || []).length === 0 ? (
        <div className="bg-white rounded-2xl p-12 text-center border border-[#3B0A2E]/8"><p className="text-[#241019]/50">No completed donations yet.</p></div>
      ) : (
        <div className="bg-white rounded-2xl border border-[#3B0A2E]/8 overflow-hidden">
          <table className="w-full text-left">
            <thead>
              <tr className="text-[#241019]/55 text-[12px] uppercase tracking-wide" style={{ background: '#faf2f7' }}>
                <th className="px-5 py-3 font-semibold">Date</th>
                <th className="px-5 py-3 font-semibold">Donor</th>
                <th className="px-5 py-3 font-semibold">Email</th>
                <th className="px-5 py-3 font-semibold">Type</th>
                <th className="px-5 py-3 font-semibold text-right">Amount</th>
              </tr>
            </thead>
            <tbody>
              {data.items.map((it) => (
                <tr key={it.session_id} className="border-t border-[#3B0A2E]/8 text-[13.5px]">
                  <td className="px-5 py-3 text-[#241019]/70 whitespace-nowrap">{it.updated_at ? new Date(it.updated_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }) : '—'}</td>
                  <td className="px-5 py-3 text-[#3B0A2E] font-medium">{it.anonymous ? 'Anonymous' : (it.donor_name || '—')}</td>
                  <td className="px-5 py-3 text-[#241019]/60">{it.donor_email || '—'}</td>
                  <td className="px-5 py-3">
                    <span className="text-[11px] font-semibold px-2.5 py-0.5 rounded-full" style={it.frequency === 'monthly' ? { background: '#f2e6ee', color: '#B4247E' } : { background: '#f0ece4', color: '#8a6d2f' }}>
                      {it.frequency === 'monthly' ? 'Monthly' : 'One-Time'}
                    </span>
                  </td>
                  <td className="px-5 py-3 text-right font-semibold text-[#3B0A2E]">${Number(it.amount).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
