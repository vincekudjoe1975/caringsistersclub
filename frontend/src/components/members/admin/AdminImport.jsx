import React, { useState } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { UploadCloud, Download, Loader2, RefreshCw, Users } from 'lucide-react';

const COLS = [['name', 'Name', 'w-36'], ['email', 'Email', 'w-48'], ['phone', 'Phone', 'w-28'], ['city', 'City', 'w-28'], ['birthday', 'Birthday', 'w-24'], ['joined', 'Join date', 'w-28'], ['office', 'Office', 'w-28'], ['referrer', 'Referrer', 'w-36']];
const TEMPLATE = 'Name,Email,Phone,City,Birthday,Join date,Office,Referrer\nJane Doe,jane@example.com,302-555-0100,Bear,03/14,2019-05-01,Treasurer,Mary Smith\n';

export function AdminImport() {
  const { toast } = useToast();
  const [rows, setRows] = useState(null);
  const [busy, setBusy] = useState(false);
  const [invite, setInvite] = useState(true);
  const [result, setResult] = useState(null);

  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file); setBusy(true); setResult(null);
    try { const { data } = await api.post('/admin/members/import/preview', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setRows(data.rows); }
    catch (ex) { toast({ title: 'Could not read file', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const strip = (r) => Object.fromEntries(COLS.map(([k]) => [k, r[k] || '']));
  const recheck = async () => { setBusy(true); try { const { data } = await api.post('/admin/members/import/validate', { rows: rows.map(strip) }); setRows(data.rows); } finally { setBusy(false); } };
  const commit = async () => {
    setBusy(true);
    try { const { data } = await api.post('/admin/members/import/commit', { rows: rows.map(strip), send_invites: invite }); setResult(data); setRows(null); toast({ title: 'Import complete' }); }
    catch (ex) { toast({ title: 'Import failed', description: ex?.response?.data?.detail, variant: 'destructive' }); }
    finally { setBusy(false); }
  };
  const edit = (i, k, v) => setRows(rows.map((r, j) => (j === i ? { ...r, [k]: v } : r)));
  const template = () => { const a = document.createElement('a'); a.href = URL.createObjectURL(new Blob([TEMPLATE], { type: 'text/csv' })); a.download = 'member-import-template.csv'; a.click(); };
  const valid = rows ? rows.filter((r) => !r.errors.length).length : 0;

  return (
    <div data-testid="admin-import">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-5">
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold flex items-center gap-2"><Users size={18} className="text-[#B4247E]" /> Import existing sisters</p>
        <p className="text-[12.5px] text-[#241019]/60 mb-4">Upload a CSV or Excel (.xlsx) file with columns Name, Email, Phone, City, Birthday, Join date, Office, Referrer. Sisters appear in the directory and dues right away; their portal opens the first time they sign in with Google using that email.</p>
        <div className="flex flex-wrap gap-3 items-center">
          <label className="btn-magenta rounded-full px-5 py-2.5 text-[13px] font-semibold flex items-center gap-1.5 cursor-pointer">
            {busy ? <Loader2 size={14} className="animate-spin" /> : <UploadCloud size={14} />} Choose file
            <input data-testid="import-file-input" type="file" accept=".csv,.xlsx" className="hidden" onChange={(e) => { upload(e.target.files?.[0]); e.target.value = ''; }} />
          </label>
          <button data-testid="import-template-btn" onClick={template} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Download size={14} /> Download template</button>
        </div>
        {result && <p data-testid="import-result" className="mt-4 text-[13.5px] text-green-700 bg-green-50 rounded-xl px-4 py-3">Added {result.created}, updated {result.updated}, skipped {result.skipped}. Linked {result.referrers_linked} referrer{result.referrers_linked === 1 ? '' : 's'}.</p>}
      </div>
      {rows && (
        <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8">
          <div className="flex flex-wrap items-center gap-3 mb-4">
            <p data-testid="import-summary" className="font-semibold text-[#3B0A2E] mr-auto">{rows.length} rows · {valid} ready · {rows.length - valid} with errors</p>
            <button data-testid="import-recheck-btn" onClick={recheck} disabled={busy} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><RefreshCw size={13} /> Re-check edits</button>
            <label className="flex items-center gap-2 text-[13px] text-[#241019]/75"><input data-testid="import-invite-toggle" type="checkbox" checked={invite} onChange={(e) => setInvite(e.target.checked)} className="accent-[#B4247E]" /> Email each sister an invitation</label>
            <button data-testid="import-commit-btn" onClick={commit} disabled={busy || !valid} className="btn-magenta rounded-full px-5 py-2 text-[13px] font-semibold disabled:opacity-50">Import {valid} sister{valid === 1 ? '' : 's'}</button>
          </div>
          <div className="overflow-auto max-h-[520px]">
            <table className="text-[12.5px] min-w-full">
              <thead className="sticky top-0 bg-white"><tr className="text-left text-[#241019]/55"><th className="p-1.5">#</th>{COLS.map(([k, l]) => <th key={k} className="p-1.5">{l}</th>)}<th className="p-1.5">Status</th></tr></thead>
              <tbody>
                {rows.map((r, i) => (
                  <tr key={i} data-testid={`import-row-${i}`} className={`border-t border-[#3B0A2E]/8 align-top ${r.errors.length ? 'bg-red-50/60' : ''}`}>
                    <td className="p-1.5 text-[#241019]/45">{r.row}</td>
                    {COLS.map(([k, , w]) => <td key={k} className="p-1"><input data-testid={`import-cell-${i}-${k}`} value={r[k] || ''} onChange={(e) => edit(i, k, e.target.value)} className={`${w} rounded border border-[#3B0A2E]/10 px-1.5 py-1 focus:outline-none focus:border-[#B4247E]`} /></td>)}
                    <td className="p-1.5 min-w-[180px]">
                      {r.errors.map((e) => <p key={e} className="text-red-700">{e}</p>)}
                      {!r.errors.length && <p className="text-green-700 font-semibold">{r.action === 'update' ? 'Will update existing' : 'Will add'}</p>}
                      {r.warnings.map((w) => <p key={w} className="text-amber-700">{w}</p>)}
                      {r.referrer_email && <p className="text-[#241019]/50">Referrer: {r.referrer_email}</p>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
