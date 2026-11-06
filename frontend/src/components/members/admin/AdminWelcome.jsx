import React, { useEffect, useState } from 'react';
import { api } from '../../../lib/api';
import { useToast } from '../../../hooks/use-toast';
import { Save, Eye, Send, RotateCcw, Loader2 } from 'lucide-react';

const inputCls = 'w-full rounded-lg border border-[#3B0A2E]/15 px-3 py-2 text-[13.5px] focus:outline-none focus:border-[#B4247E]';
const KINDS = [
  { k: 'welcome', l: 'Welcome packet', d: 'Sent when a sister is approved, accepts an invitation, or is imported with invitations on. The bylaws summary, her dues and upcoming gatherings are added automatically. To resend, use "Send welcome" next to her name in People.' },
  { k: 'approval', l: 'Approval notice', d: 'Sent the moment staff approve her application, with a button to open the member portal.' },
];
const err = (ex) => ex?.response?.data?.detail;

function EmailEditor({ kind }) {
  const { toast } = useToast();
  const [f, setF] = useState(null);
  const [defaults, setDefaults] = useState(null);
  const [view, setView] = useState({ html: '', subject: '' });
  const [sending, setSending] = useState(false);
  const body = (x) => ({ subject: x.subject, greeting: x.greeting, message: x.message });
  const preview = async (x = f) => { const { data } = await api.post(`/admin/member-emails/${kind.k}/preview`, body(x)); setView(data); };
  useEffect(() => {
    let live = true;
    api.get(`/admin/member-emails/${kind.k}`).then(({ data }) => { if (!live) return; setDefaults(data.defaults); setF(body(data)); preview(body(data)); });
    return () => { live = false; };
  }, [kind.k]); // eslint-disable-line react-hooks/exhaustive-deps
  const save = async () => {
    try { await api.put(`/admin/member-emails/${kind.k}`, body(f)); toast({ title: `${kind.l} email saved` }); preview(); }
    catch (ex) { toast({ title: 'Could not save', description: err(ex), variant: 'destructive' }); }
  };
  const test = async () => {
    setSending(true);
    try { const { data } = await api.post(`/admin/member-emails/${kind.k}/test`, body(f)); toast({ title: 'Test email sent', description: `Check ${data.sent_to}` }); }
    catch (ex) { toast({ title: 'Could not send test', description: err(ex), variant: 'destructive' }); }
    finally { setSending(false); }
  };
  const reset = () => { setF(body(defaults)); preview(body(defaults)); };
  if (!f) return <p className="text-[#241019]/50">Loading…</p>;
  const field = (k, label, rows) => (
    <label className="text-[12.5px] font-semibold text-[#3B0A2E] block">{label}
      {rows ? <textarea data-testid={`${kind.k}-email-${k}`} rows={rows} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} className={`${inputCls} mt-1`} />
        : <input data-testid={`${kind.k}-email-${k}`} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} className={`${inputCls} mt-1`} />}
    </label>
  );
  return (
    <div className="grid lg:grid-cols-[1fr_1.2fr] gap-6" data-testid={`${kind.k}-email-editor`}>
      <div className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 space-y-3 self-start">
        <p className="text-[12.5px] text-[#241019]/55">{kind.d} The "Get the app" button and QR code are always included. Use {'{first}'} for her first name.</p>
        {field('subject', 'Subject')}
        {field('greeting', 'Greeting')}
        {field('message', 'Message', 8)}
        <div className="flex flex-wrap gap-2 pt-1">
          <button data-testid={`${kind.k}-email-preview-btn`} onClick={() => preview()} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5"><Eye size={14} /> Preview</button>
          <button data-testid={`${kind.k}-email-save-btn`} onClick={save} className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5"><Save size={14} /> Save</button>
          <button data-testid={`${kind.k}-email-test-btn`} disabled={sending} onClick={test} className="rounded-full px-4 py-2 text-[13px] font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] flex items-center gap-1.5 disabled:opacity-60">{sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />} Send me a test</button>
          <button data-testid={`${kind.k}-email-reset-btn`} onClick={reset} className="rounded-full px-3 py-2 text-[13px] font-semibold text-[#241019]/60 flex items-center gap-1.5 hover:text-[#B4247E]"><RotateCcw size={14} /> Use original wording</button>
        </div>
      </div>
      <div className="space-y-2">
        <p data-testid={`${kind.k}-email-preview-subject`} className="text-[13px] text-[#241019]/70"><span className="font-semibold text-[#3B0A2E]">Subject:</span> {view.subject}</p>
        <iframe data-testid={`${kind.k}-email-preview`} title={`${kind.l} preview`} srcDoc={view.html} sandbox="" className="w-full h-[720px] rounded-2xl border border-[#3B0A2E]/8 bg-white" />
      </div>
    </div>
  );
}

export function AdminWelcome() {
  const [k, setK] = useState('welcome');
  const kind = KINDS.find((x) => x.k === k);
  return (
    <div data-testid="admin-welcome" className="space-y-4">
      <div className="flex flex-wrap gap-2">
        {KINDS.map((x) => (
          <button key={x.k} data-testid={`member-email-tab-${x.k}`} onClick={() => setK(x.k)}
            className={`rounded-full px-4 py-2 text-[13px] font-semibold transition-colors ${k === x.k ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/15'}`}>{x.l}</button>
        ))}
      </div>
      <EmailEditor key={k} kind={kind} />
    </div>
  );
}
