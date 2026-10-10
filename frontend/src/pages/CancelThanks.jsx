import React, { useEffect, useState } from 'react';
import { Loader2, HeartHandshake, CheckCircle2, AlertCircle, Send } from 'lucide-react';
import { api } from '../lib/api';
import { errMsg } from './Events';

const inp = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

export default function CancelThanks() {
  const token = new URLSearchParams(window.location.search).get('token') || '';
  const [info, setInfo] = useState(null);
  const [form, setForm] = useState({ subject: '', message: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  useEffect(() => {
    api.get(`/cancellations/token/${encodeURIComponent(token)}`)
      .then(({ data }) => { setInfo(data); setForm({ subject: data.subject, message: data.message }); })
      .catch((e) => setError(errMsg(e)));
  }, [token]);

  const send = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { await api.post(`/cancellations/token/${encodeURIComponent(token)}`, form); setSent(true); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  const shell = (children) => (
    <section className="min-h-[70vh] px-5 py-32" style={{ background: '#F7EFE9' }}>
      <div className="bg-white rounded-[24px] max-w-2xl mx-auto p-8 lg:p-10 border border-[#3B0A2E]/8" data-testid="cancel-thanks-page">{children}</div>
    </section>
  );

  if (!info && error) return shell(<div className="text-center"><AlertCircle size={40} className="text-[#B4247E] mx-auto mb-3" /><p className="text-[15px] text-[#3B0A2E]" data-testid="cancel-thanks-error">{error}</p></div>);
  if (!info) return shell(<Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} />);
  if (sent || info.thanked) {
    return shell(
      <div className="text-center" data-testid="cancel-thanks-sent">
        <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
        <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1">Thank-you note sent</p>
        <p className="text-[14px] text-[#241019]/65">{info.name} ({info.email}) has received your note{info.thanked_at && !sent ? ` on ${new Date(info.thanked_at).toLocaleDateString()}` : ''}.</p>
      </div>
    );
  }
  return shell(
    <form onSubmit={send}>
      <div className="flex items-center gap-3 mb-2">
        <HeartHandshake size={28} className="text-[#B4247E]" />
        <h1 className="font-serif text-[24px] text-[#3B0A2E] font-semibold">Thank {info.name}</h1>
      </div>
      <p className="text-[13.5px] text-[#241019]/65 mb-6" data-testid="cancel-thanks-summary">
        ${info.amount.toLocaleString()} / month{info.ends_on && <> &middot; ends {info.ends_on}</>} &middot; {info.email}{info.reason && <> &middot; Reason: {info.reason}</>}
      </p>
      <label className="text-[13px] font-semibold text-[#3B0A2E]">Subject</label>
      <input required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} className={inp} data-testid="thanks-subject-input" />
      <label className="text-[13px] font-semibold text-[#3B0A2E] block mt-4">Message</label>
      <textarea required rows={11} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} className={`${inp} resize-y leading-relaxed`} data-testid="thanks-message-input" />
      {error && <p className="text-[13px] text-red-600 mt-3" data-testid="cancel-thanks-error">{error}</p>}
      <button type="submit" disabled={busy} data-testid="send-thanks-btn" className="btn-magenta rounded-full px-7 py-3 font-semibold text-[14px] mt-5 flex items-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Send Thank-You Note
      </button>
    </form>
  );
}
