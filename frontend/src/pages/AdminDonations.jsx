import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, DollarSign, Repeat, Gift, TrendingUp, Download, Mail } from 'lucide-react';

export default function AdminDonations() {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [sending, setSending] = useState(false);
  const [reminding, setReminding] = useState(false);
  const thisYear = new Date().getFullYear();

  const exportCsv = async () => {
    setExporting(true);
    try {
      const res = await api.get('/admin/donations/export', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'text/csv' }));
      const a = document.createElement('a');
      a.href = url;
      a.download = 'caring-sisters-donations.csv';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: 'Export failed', description: 'Please try again.', variant: 'destructive' });
    } finally {
      setExporting(false);
    }
  };

  const sendStatements = async () => {
    if (!window.confirm(`Email ${thisYear} giving statements to all donors with an email on file?`)) return;
    setSending(true);
    try {
      const { data: r } = await api.post(`/admin/donations/send-statements?year=${thisYear}`);
      toast({ title: 'Statements sent', description: `${r.sent} of ${r.recipients} donors emailed for ${r.year}.` });
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  const sendReminders = async () => {
    if (!window.confirm('Send renewal reminders now to monthly donors whose gift renews in ~3 days?')) return;
    setReminding(true);
    try {
      const { data: r } = await api.post('/admin/recurring/send-reminders');
      toast({ title: 'Reminders processed', description: `${r.sent} reminder(s) sent across ${r.subscriptions_checked} subscription(s).` });
    } catch (e) {
      toast({ title: 'Failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setReminding(false);
    }
  };

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

      <div className="flex flex-wrap items-center justify-between gap-3 mb-5">
        <div className="flex gap-2">
          {[{ k: 'all', l: 'All' }, { k: 'one-time', l: 'One-Time' }, { k: 'monthly', l: 'Monthly' }].map((f) => (
            <button key={f.k} onClick={() => setFilter(f.k)}
              className={`px-4 py-2 rounded-full text-[13.5px] font-semibold transition-all ${filter === f.k ? 'text-white' : 'text-[#3B0A2E] bg-white'}`}
              style={filter === f.k ? { background: '#B4247E' } : { border: '1px solid rgba(59,10,46,0.1)' }}>
              {f.l}
            </button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={exportCsv} disabled={exporting}
            className="px-4 py-2 rounded-full text-[13.5px] font-semibold flex items-center gap-2 bg-white text-[#3B0A2E] disabled:opacity-60" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>
            {exporting ? <Loader2 size={15} className="animate-spin" /> : <Download size={15} />} Export CSV
          </button>
          <button onClick={sendStatements} disabled={sending}
            className="px-4 py-2 rounded-full text-[13.5px] font-semibold flex items-center gap-2 bg-white text-[#3B0A2E] disabled:opacity-60" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>
            {sending ? <Loader2 size={15} className="animate-spin" /> : <Mail size={15} />} Email {thisYear} Statements
          </button>
          <button onClick={sendReminders} disabled={reminding}
            className="px-4 py-2 rounded-full text-[13.5px] font-semibold flex items-center gap-2 btn-magenta disabled:opacity-60">
            {reminding ? <Loader2 size={15} className="animate-spin" /> : <Repeat size={15} />} Send Renewal Reminders
          </button>
        </div>
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
