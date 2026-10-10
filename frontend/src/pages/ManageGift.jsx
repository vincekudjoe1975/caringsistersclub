import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Loader2, ShieldCheck, Mail, CreditCard, FileText, XCircle, CheckCircle2, AlertCircle } from 'lucide-react';
import PageHero from '../components/PageHero';
import { api } from '../lib/api';
import { errMsg } from './Events';

const FEATURES = [
  { Icon: CreditCard, t: 'Update your card' },
  { Icon: FileText, t: 'Download past receipts' },
  { Icon: XCircle, t: 'Cancel anytime' },
];

function RequestForm() {
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState('');
  const [error, setError] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { const { data } = await api.post('/donor/manage-link', { email }); setSent(data.message); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };

  if (sent) {
    return (
      <div className="text-center" data-testid="manage-link-sent">
        <Mail size={42} className="text-[#B4247E] mx-auto mb-3" />
        <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">Check your inbox</p>
        <p className="text-[14px] text-[#241019]/65">{sent} The link expires in 1 hour.</p>
      </div>
    );
  }
  return (
    <form onSubmit={submit} className="space-y-4">
      <label className="text-[13px] font-semibold text-[#3B0A2E] block">Email used for your monthly gift</label>
      <input required type="email" value={email} onChange={(e) => setEmail(e.target.value)} data-testid="manage-email-input"
        className="w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E]" placeholder="you@example.com" />
      {error && <p className="text-[13px] text-red-600" data-testid="manage-error">{error}</p>}
      <button type="submit" disabled={busy} data-testid="manage-send-link-btn" className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
        {busy ? <><Loader2 size={16} className="animate-spin" /> Sending…</> : 'Email Me a Secure Link'}
      </button>
    </form>
  );
}

function OpenPortal({ token }) {
  const [state, setState] = useState('checking');
  const [error, setError] = useState('');

  useEffect(() => {
    api.get(`/donor/manage-token/${encodeURIComponent(token)}`).then(({ data }) => setState(data.valid ? 'ready' : 'invalid')).catch(() => setState('invalid'));
  }, [token]);

  const open = async () => {
    setState('opening');
    try { const { data } = await api.post('/donor/portal', { token }); window.location.href = data.url; }
    catch (err) { setError(errMsg(err)); setState('ready'); }
  };

  if (state === 'checking') return <Loader2 className="animate-spin text-[#B4247E] mx-auto" size={30} />;
  if (state === 'invalid') {
    return (
      <div className="text-center" data-testid="manage-token-invalid">
        <AlertCircle size={40} className="text-[#B4247E] mx-auto mb-3" />
        <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-2">This link has expired or was already used</p>
        <p className="text-[14px] text-[#241019]/65 mb-5">Request a fresh one below.</p>
        <RequestForm />
      </div>
    );
  }
  return (
    <div className="text-center">
      <ShieldCheck size={42} className="text-[#B4247E] mx-auto mb-3" />
      <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">You're verified</p>
      <p className="text-[14px] text-[#241019]/65 mb-6">Continue to Stripe's secure page to manage your monthly gift.</p>
      {error && <p className="text-[13px] text-red-600 mb-3" data-testid="manage-error">{error}</p>}
      <button onClick={open} disabled={state === 'opening'} data-testid="open-portal-btn" className="btn-magenta rounded-full px-8 py-3.5 font-semibold inline-flex items-center gap-2 disabled:opacity-60">
        {state === 'opening' ? <><Loader2 size={16} className="animate-spin" /> Opening…</> : 'Open Secure Billing Page'}
      </button>
    </div>
  );
}

export default function ManageGift() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  const done = params.get('done');
  return (
    <div>
      <PageHero kicker="Monthly Donors" title="Manage your monthly gift" subtitle="Update your payment method, download receipts, or change your plans, securely through Stripe." />
      <section className="py-16 lg:py-20">
        <div className="max-w-xl mx-auto px-5">
          <div className="bg-white rounded-[24px] p-8 lg:p-10 border border-[#3B0A2E]/8" data-testid="manage-gift-card">
            {done ? (
              <div className="text-center" data-testid="manage-done">
                <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
                <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-2">All set. Thank you!</p>
                <p className="text-[14px] text-[#241019]/65 mb-6">Your changes were saved with Stripe. Your generosity keeps our sisterhood thriving.</p>
                <Link to="/" className="btn-magenta rounded-full px-6 py-3 font-semibold text-[14px]">Back to Home</Link>
              </div>
            ) : token ? <OpenPortal token={token} /> : <RequestForm />}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-6">
            {FEATURES.map(({ Icon, t }) => (
              <div key={t} className="text-center text-[12.5px] text-[#3B0A2E]">
                <Icon size={20} className="text-[#CBA24B] mx-auto mb-1.5" />{t}
              </div>
            ))}
          </div>
          <p className="text-center text-[12px] text-[#241019]/50 mt-6">We never see or store your card details. Payments are handled by Stripe.</p>
        </div>
      </section>
    </div>
  );
}
