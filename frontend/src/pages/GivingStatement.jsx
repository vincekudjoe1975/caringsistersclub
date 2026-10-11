import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { FileText, Download, Loader2, Mail } from 'lucide-react';
import { api } from '../lib/api';

export const StatementRequest = () => {
  const [email, setEmail] = useState('');
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setMsg('');
    try { const { data } = await api.post('/donor/statement-link', { email }); setMsg(data.message); }
    catch (ex) { setMsg(ex?.response?.data?.detail || 'Please try again in a few minutes.'); }
    finally { setBusy(false); }
  };
  return (
    <section data-testid="statement-request" className="py-14 bg-white">
      <div className="max-w-3xl mx-auto px-5 lg:px-8">
        <div className="rounded-3xl border border-[#3B0A2E]/10 p-6 sm:p-8 grid sm:grid-cols-[auto_1fr] gap-5 items-start">
          <span className="w-12 h-12 rounded-2xl bg-[#faf2f7] flex items-center justify-center"><FileText className="text-[#B4247E]" size={22} /></span>
          <div className="min-w-0">
            <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold">Need your year-end tax summary?</h2>
            <p className="text-[14px] text-[#241019]/65 mt-1">Enter the email you gave with. We'll send a secure link so you can download a PDF statement for any year.</p>
            <form onSubmit={submit} className="mt-4 flex flex-col sm:flex-row gap-2.5">
              <input data-testid="statement-email" type="email" required autoComplete="email" inputMode="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} className="flex-1 min-w-0 rounded-full border border-[#3B0A2E]/15 px-5 py-3 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              <button data-testid="statement-submit" disabled={busy} className="btn-magenta rounded-full px-6 py-3 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">{busy ? <Loader2 size={15} className="animate-spin" /> : <Mail size={15} />} Email my link</button>
            </form>
            {msg && <p data-testid="statement-msg" className="text-[13.5px] text-[#3B0A2E] mt-3">{msg}</p>}
          </div>
        </div>
      </div>
    </section>
  );
};

export default function GivingStatement() {
  const [sp] = useSearchParams();
  const t = sp.get('t') || '';
  const [d, setD] = useState(null);
  const [err, setErr] = useState('');
  useEffect(() => { api.get(`/donor/statements/${t}`).then(({ data }) => setD(data)).catch((ex) => setErr(ex?.response?.data?.detail || 'This link is not valid.')); }, [t]);
  const base = `${process.env.REACT_APP_BACKEND_URL}/api/donor/statements/${t}`;
  return (
    <div className="min-h-[70vh] bg-[#F7EFE9] py-16 px-5" data-testid="giving-statement-page">
      <div className="max-w-xl mx-auto bg-white rounded-3xl p-7 sm:p-10 border border-[#3B0A2E]/8">
        <p className="eyebrow text-[#B4247E] mb-2">Giving statements</p>
        <h1 className="font-serif text-[30px] text-[#3B0A2E] font-semibold">Your tax summaries</h1>
        {err ? (
          <div data-testid="statement-error"><p className="text-[14.5px] text-[#241019]/70 mt-3">{err}</p><Link to="/donate" className="inline-block mt-5 btn-magenta rounded-full px-6 py-3 font-semibold">Request a new link</Link></div>
        ) : !d ? <div className="py-10 flex justify-center"><Loader2 className="animate-spin text-[#B4247E]" /></div> : (
          <>
            <p className="text-[14px] text-[#241019]/60 mt-2">For {d.email}. Thank you for your generosity!</p>
            <ul className="mt-6 space-y-3">
              {d.years.map((y) => (
                <li key={y.year} data-testid={`statement-year-${y.year}`} className="flex items-center gap-4 rounded-2xl border border-[#3B0A2E]/10 px-5 py-4">
                  <div className="flex-1 min-w-0"><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold leading-none">{y.year}</p><p className="text-[13px] text-[#241019]/60 mt-1">{y.count} gift{y.count === 1 ? '' : 's'} · ${y.total.toLocaleString('en-US', { minimumFractionDigits: 2 })}</p></div>
                  <a data-testid={`statement-download-${y.year}`} href={`${base}/${y.year}.pdf`} className="btn-magenta rounded-full px-5 py-2.5 font-semibold text-[14px] flex items-center gap-2"><Download size={15} /> PDF</a>
                </li>
              ))}
            </ul>
          </>
        )}
      </div>
    </div>
  );
}
