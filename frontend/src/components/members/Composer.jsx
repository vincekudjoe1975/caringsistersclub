import React, { useState } from 'react';
import { Loader2, Send } from 'lucide-react';

const inputCls = 'w-full rounded-xl border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] bg-white focus:outline-none focus:border-[#B4247E] transition-colors';

export function Composer({ withTitle, onSubmit, onCancel, placeholder = 'Share your thoughts…' }) {
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const submit = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try { await onSubmit(withTitle ? { title, body } : { body }); setTitle(''); setBody(''); }
    catch (ex) { setErr(ex?.response?.data?.detail || 'Could not post. Please try again.'); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} data-testid={withTitle ? 'thread-composer' : 'reply-composer'} className="bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 mb-6 space-y-3">
      {withTitle && <input data-testid="composer-title" placeholder="Title" value={title} onChange={(e) => setTitle(e.target.value)} className={inputCls} />}
      <textarea data-testid="composer-body" rows={withTitle ? 4 : 3} placeholder={placeholder} value={body} onChange={(e) => setBody(e.target.value)} className={inputCls} />
      {err && <p data-testid="composer-error" className="text-red-600 text-[13px]">{err}</p>}
      <div className="flex gap-2 justify-end">
        {onCancel && <button type="button" data-testid="composer-cancel" onClick={onCancel} className="rounded-full px-5 py-2 text-[13.5px] font-semibold text-[#3B0A2E] border border-[#3B0A2E]/15">Cancel</button>}
        <button data-testid="composer-submit" disabled={busy} className="btn-magenta rounded-full px-5 py-2 text-[13.5px] font-semibold flex items-center gap-1.5 disabled:opacity-60">
          {busy ? <Loader2 className="animate-spin" size={14} /> : <Send size={14} />} Post
        </button>
      </div>
    </form>
  );
}
