import React, { useState } from 'react';
import { api } from '../lib/api';
import { GitMerge, Loader2, ArrowRight } from 'lucide-react';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

const Summary = ({ a, label, testid }) => (
  <div data-testid={testid} className="rounded-xl bg-[#faf2f7] p-3.5 text-[12.5px] text-[#241019]/75 flex-1 min-w-[200px]">
    <p className="eyebrow text-[#B4247E] mb-1">{label}</p>
    <p className="font-semibold text-[14px] text-[#3B0A2E]">{a.name || a.email}</p>
    <p className="break-all">{a.email}</p>
    <p>Role: {a.role === 'admin' ? 'Team (admin)' : 'Member account'} · Membership: {a.member_status}</p>
    <p>Signs in with: {a.signed_up_with}{a.has_password ? ' (has password)' : ''}</p>
    <p>Devices: {a.devices.length ? a.devices.join(', ') : 'none'}</p>
  </div>
);

export function MergeAccounts({ toast, onDone }) {
  const [f, setF] = useState({ keep_email: '', dup_email: '' });
  const [pv, setPv] = useState(null);
  const [busy, setBusy] = useState(false);
  const err = (ex) => toast({ title: 'Could not merge', description: ex?.response?.data?.detail, variant: 'destructive' });
  const preview = async (e) => {
    e.preventDefault(); setBusy(true); setPv(null);
    try { const { data } = await api.post('/admin/team/merge/preview', f); setPv(data); } catch (ex) { err(ex); } finally { setBusy(false); }
  };
  const merge = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/team/merge', f); toast({ title: 'Accounts merged', description: `${data.moved} records moved to ${data.keep.email}. The other email now signs in to this same account.` }); setPv(null); setF({ keep_email: '', dup_email: '' }); onDone?.(); }
    catch (ex) { err(ex); } finally { setBusy(false); }
  };
  return (
    <form onSubmit={preview} data-testid="merge-accounts" className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
      <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-2 flex items-center gap-2"><GitMerge size={18} className="text-[#B4247E]" /> Merge duplicate accounts</h3>
      <p className="text-[12.5px] text-[#241019]/60 mb-4">Moves devices, profile, RSVPs, votes and posts from the duplicate into the account you keep. Both emails then sign in to the same account.</p>
      <div className="space-y-2.5">
        <input data-testid="merge-keep-email" type="email" required placeholder="Account to keep (email)" value={f.keep_email} onChange={(e) => { setPv(null); setF({ ...f, keep_email: e.target.value }); }} className={inputCls} />
        <input data-testid="merge-dup-email" type="email" required placeholder="Duplicate to merge in (email)" value={f.dup_email} onChange={(e) => { setPv(null); setF({ ...f, dup_email: e.target.value }); }} className={inputCls} />
        <button data-testid="merge-preview-btn" disabled={busy} className="rounded-full w-full py-2.5 font-semibold text-[14px] border border-[#3B0A2E]/20 text-[#3B0A2E] hover:bg-[#F7EFE9] transition-colors disabled:opacity-60">{busy && !pv ? <Loader2 size={14} className="animate-spin inline" /> : 'Preview merge'}</button>
      </div>
      {pv && (
        <div className="mt-4 space-y-3" data-testid="merge-preview">
          <div className="flex flex-wrap items-center gap-2"><Summary a={pv.dup} label="Duplicate (removed)" testid="merge-preview-dup" /><ArrowRight size={16} className="text-[#B4247E]" /><Summary a={pv.keep} label="Keep" testid="merge-preview-keep" /></div>
          <button type="button" data-testid="merge-confirm-btn" disabled={busy} onClick={merge} className="btn-magenta rounded-full w-full py-2.5 font-semibold text-[14px] flex items-center justify-center gap-2 disabled:opacity-60">{busy ? <Loader2 size={14} className="animate-spin" /> : <GitMerge size={14} />} Merge into {pv.keep.email}</button>
        </div>
      )}
    </form>
  );
}
