import React, { useCallback, useEffect, useState } from 'react';
import { Calculator, Send, Download, Loader2 } from 'lucide-react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';

const input = 'w-full rounded-xl border border-[#3B0A2E]/15 px-3 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E]';
const FILES = [['summary', 'Summary'], ['donations', 'Donations'], ['donor-totals', 'Donor totals'], ['tickets', 'Ticket sales'], ['dues', 'Member dues']];

export const AccountantPackage = () => {
  const { toast } = useToast();
  const [c, setC] = useState(null);
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [busy, setBusy] = useState(false);
  const load = useCallback(() => api.get('/admin/accounting').then(({ data }) => setC({ ...data, emailsText: data.emails.join(', '), ccText: data.cc.join(', ') })).catch(() => {}), []);
  useEffect(() => { load(); }, [load]);
  if (!c) return null;
  const split = (t) => t.split(/[,\s]+/).filter(Boolean);
  const save = async () => {
    try { await api.put('/admin/accounting', { name: c.name, emails: split(c.emailsText), cc: split(c.ccText), enabled: c.enabled }); toast({ title: 'Accountant settings saved' }); load(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  const send = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/accounting/send', { year: Number(year) }); toast({ title: `${data.year} package sent`, description: data.sent_to.join(', ') }); load(); }
    catch (ex) { toast({ title: 'Could not send', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const dl = async (name) => {
    const res = await api.get(`/admin/accounting/${year}/${name}`, { responseType: 'blob' });
    const url = URL.createObjectURL(res.data); const a = document.createElement('a'); a.href = url; a.download = `caring-sisters-${year}-${name}`; a.click(); URL.revokeObjectURL(url);
  };
  const years = Array.from({ length: 6 }, (_, i) => new Date().getFullYear() - i);
  return (
    <section data-testid="accountant-package" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 mb-6">
      <h3 className="font-serif text-[20px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Calculator size={18} className="text-[#B4247E]" /> Year-end tax package for your accountant</h3>
      <p className="text-[13.5px] text-[#241019]/65 mt-1">Every January 5 at 9am Eastern, the prior year's CSV package (summary, donations, donor totals, ticket sales, dues) is emailed with secure download links.</p>
      <div className="grid sm:grid-cols-3 gap-3 mt-4">
        <label className="text-[12px] font-semibold text-[#3B0A2E]">Company<input data-testid="acct-name" value={c.name} onChange={(e) => setC({ ...c, name: e.target.value })} className={input} /></label>
        <label className="text-[12px] font-semibold text-[#3B0A2E]">Accountant emails<input data-testid="acct-emails" value={c.emailsText} onChange={(e) => setC({ ...c, emailsText: e.target.value })} className={input} /></label>
        <label className="text-[12px] font-semibold text-[#3B0A2E]">Copy to<input data-testid="acct-cc" value={c.ccText} onChange={(e) => setC({ ...c, ccText: e.target.value })} className={input} /></label>
      </div>
      <div className="flex flex-wrap items-center gap-3 mt-3">
        <label className="flex items-center gap-2 text-[13.5px] text-[#3B0A2E]"><input data-testid="acct-enabled" type="checkbox" checked={c.enabled} onChange={(e) => setC({ ...c, enabled: e.target.checked })} className="accent-[#B4247E] w-5 h-5" /> Send automatically every January 5</label>
        <button data-testid="acct-save" onClick={save} className="ml-auto rounded-full px-5 py-2 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] hover:bg-[#F7EFE9]">Save</button>
      </div>
      <div className="flex flex-wrap items-center gap-2 mt-5 pt-4 border-t border-[#3B0A2E]/10">
        <select data-testid="acct-year" value={year} onChange={(e) => setYear(e.target.value)} className={`${input} w-auto`}>{years.map((y) => <option key={y} value={y}>Tax year {y}</option>)}</select>
        <button data-testid="acct-send" disabled={busy} onClick={send} className="btn-magenta rounded-full px-5 py-2.5 font-semibold flex items-center gap-1.5 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send now</button>
        <button data-testid="acct-dl-zip" onClick={() => dl('all.zip')} className="rounded-full px-4 py-2.5 font-semibold border border-[#3B0A2E]/20 text-[#3B0A2E] flex items-center gap-1.5"><Download size={14} /> ZIP</button>
        {FILES.map(([k, l]) => <button key={k} data-testid={`acct-dl-${k}`} onClick={() => dl(`${k}.csv`)} className="rounded-full px-3 py-2 text-[12.5px] font-semibold text-[#B4247E] hover:bg-[#faf2f7]">{l}</button>)}
      </div>
      {c.history?.length > 0 && <p data-testid="acct-history" className="text-[12.5px] text-[#241019]/55 mt-3">Last sent: {c.history[0].year} package on {new Date(c.history[0].sent_at).toLocaleDateString()} to {c.history[0].sent_to.join(', ')}</p>}
    </section>
  );
};
