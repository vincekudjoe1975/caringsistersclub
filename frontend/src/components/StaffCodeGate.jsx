import React, { useState } from 'react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import Logo from './Logo';
import { ShieldCheck, Loader2, Mail } from 'lucide-react';
import { Notice, apiError } from './EmailAuth';

export function StaffCodeGate() {
  const { user, checkAuth, logout } = useAuth();
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState({ kind: '', text: '' });
  const resend = async () => {
    try { await api.post('/auth/staff-code/request'); setMsg({ kind: 'ok', text: `We sent a new code to ${user.email}.` }); }
    catch (e) { setMsg({ kind: 'error', text: apiError(e) }); }
  };
  const verify = async (e) => {
    e.preventDefault();
    if (code.length !== 6) return setMsg({ kind: 'error', text: 'Please enter the 6-digit code from your email.' });
    setBusy(true);
    try { await api.post('/auth/staff-code/verify', { code }); await checkAuth(); }
    catch (ex) { setMsg({ kind: 'error', text: apiError(ex) }); setBusy(false); }
  };
  return (
    <div data-testid="staff-code-gate" className="csc-hero-gradient min-h-screen flex items-center justify-center p-5">
      <form onSubmit={verify} className="bg-white rounded-3xl p-7 sm:p-10 w-full max-w-md text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
        <div className="flex justify-center mb-6"><Logo compact /></div>
        <span className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-5" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><ShieldCheck size={26} className="text-white" /></span>
        <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-2">Check your email</h1>
        <p data-testid="staff-code-gate-hint" className="text-[14px] text-[#241019]/65 mb-6">For extra safety, Admin needs the 6-digit code we just sent to <b>{user.email}</b>.</p>
        <input data-testid="staff-code-input" value={code} onChange={(e) => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} inputMode="numeric" autoComplete="one-time-code" placeholder="123456" autoFocus
          className="w-full text-center font-serif text-[28px] tracking-[0.5em] rounded-xl border border-[#3B0A2E]/15 px-3 py-3 focus:outline-none focus:border-[#B4247E]" />
        {msg.text && <div className="mt-3 text-left"><Notice kind={msg.kind === 'error' ? 'error' : 'ok'} testid="staff-code-msg">{msg.text}</Notice></div>}
        <button type="submit" data-testid="staff-code-submit" disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold mt-5 flex items-center justify-center gap-2 disabled:opacity-60">
          {busy ? <Loader2 size={16} className="animate-spin" /> : <ShieldCheck size={16} />} Open Admin
        </button>
        <div className="flex items-center justify-between mt-5 text-[13px]">
          <button type="button" data-testid="staff-code-resend" onClick={resend} className="font-semibold text-[#B4247E] flex items-center gap-1.5 hover:underline"><Mail size={14} /> Send a new code</button>
          <button type="button" data-testid="staff-code-signout" onClick={logout} className="text-[#241019]/55 hover:text-[#3B0A2E]">Sign out</button>
        </div>
      </form>
    </div>
  );
}
