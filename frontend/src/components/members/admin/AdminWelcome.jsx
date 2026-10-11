import React, { useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Save, Eye } from 'lucide-react';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';

export function AdminWelcome() {
  const { toast } = useToast();
  const [f, setF] = useState(null);
  const [html, setHtml] = useState('');
  useEffect(() => { api.get('/admin/members/welcome').then(({ data }) => setF(data)); }, []);
  const preview = async () => { const { data } = await api.post('/admin/members/welcome/preview', f); setHtml(data.html); };
  const save = async () => {
    try { await api.put('/admin/members/welcome', f); toast({ title: 'Welcome message saved' }); preview(); }
    catch (ex) { toast({ title: 'Could not save', description: ex?.response?.data?.detail, variant: 'destructive' }); }
  };
  useEffect(() => { if (f && !html) preview(); }, [f]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!f) return <p className="text-[#241019]/50">Loading…</p>;
  return (
    <div className="grid lg:grid-cols-[1fr_1.2fr] gap-6" data-testid="admin-welcome">
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 space-y-3 self-start">
        <p className="font-serif text-[19px] text-[#3B0A2E] font-semibold">Welcome packet email</p>
        <p className="text-[12.5px] text-[#241019]/55">Sent automatically when a sister is approved, accepts an invitation, or is imported with invitations on. The bylaws summary, her dues and upcoming gatherings are added automatically. Use {'{first}'} in the subject for her first name. To resend, use "Send welcome" next to her name in People.</p>
        <label className="text-[12.5px] font-semibold text-[#3B0A2E] block">Subject<input data-testid="welcome-subject" value={f.subject} onChange={(e) => setF({ ...f, subject: e.target.value })} className={`${inputCls} mt-1`} /></label>
        <label className="text-[12.5px] font-semibold text-[#3B0A2E] block">Personal message<textarea data-testid="welcome-message" rows={8} value={f.message} onChange={(e) => setF({ ...f, message: e.target.value })} className={`${inputCls} mt-1`} /></label>
        <div className="flex gap-2">
          <button data-testid="welcome-preview-btn" onClick={preview} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Eye size={14} /> Preview</button>
          <button data-testid="welcome-save-btn" onClick={save} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Save size={14} /> Save</button>
        </div>
      </div>
      <iframe data-testid="welcome-preview" title="Welcome preview" srcDoc={html} sandbox="" className="w-full h-[720px] rounded-2xl border border-[#3B0A2E]/8 bg-white" />
    </div>
  );
}
