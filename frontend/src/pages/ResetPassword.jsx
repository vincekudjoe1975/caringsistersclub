import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import Logo from '../components/Logo';
import { PasswordField, Notice, apiError, pwOk } from '../components/EmailAuth';
import { KeyRound, Loader2 } from 'lucide-react';

export const AuthShell = ({ icon: Icon, title, children, testid }) => (
  <div className="csc-hero-gradient min-h-screen flex items-center justify-center px-5 py-16 relative overflow-hidden">
    <div className="absolute -right-24 -top-24 w-96 h-96 rounded-full opacity-30" style={{ background: 'radial-gradient(circle,#D14FA0,transparent 70%)' }} />
    <div data-testid={testid} className="relative bg-white rounded-3xl p-8 sm:p-10 w-full max-w-md text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
      <div className="flex justify-center mb-6"><Logo variant="dark" /></div>
      <span className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-5" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Icon size={26} className="text-white" /></span>
      <h1 className="font-serif text-[26px] text-[#3B0A2E] font-semibold mb-5">{title}</h1>
      {children}
    </div>
  </div>
);

export default function ResetPassword() {
  const [params] = useSearchParams();
  const token = params.get('token') || '';
  const [pw, setPw] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [done, setDone] = useState('');

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    if (!pwOk(pw)) return setErr('Password must be at least 8 characters and include at least 1 letter and 1 number.');
    if (pw !== confirm) return setErr("Passwords don't match.");
    setBusy(true);
    try { const { data } = await api.post('/auth/reset-password', { token, password: pw }); setDone(data.message); }
    catch (e2) { setErr(apiError(e2)); }
    finally { setBusy(false); }
  };

  if (!token) return <AuthShell icon={KeyRound} title="Reset Password" testid="reset-password-card"><Notice kind="error" testid="reset-password-error">This reset link is missing its code. Please request a new one from the sign-in page.</Notice><Link to="/members" data-testid="reset-password-signin-link" className="inline-block mt-5 text-[14px] font-semibold text-[#B4247E]">Go to sign in</Link></AuthShell>;

  return (
    <AuthShell icon={KeyRound} title="Reset Password" testid="reset-password-card">
      {done ? (
        <div className="space-y-5">
          <Notice kind="ok" testid="reset-password-success">{done}</Notice>
          <Link to="/members" data-testid="reset-password-signin-link" className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center">Log in now</Link>
        </div>
      ) : (
        <form onSubmit={submit} className="space-y-4" noValidate data-testid="reset-password-form">
          <PasswordField label="New password" testid="reset-password-input" value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" />
          <p className="text-[12px] text-left -mt-2 text-[#241019]/55">At least 8 characters, with at least 1 letter and 1 number.</p>
          <PasswordField label="Confirm new password" testid="reset-password-confirm" value={confirm} onChange={(e) => setConfirm(e.target.value)} autoComplete="new-password" />
          {err && <Notice kind="error" testid="reset-password-error">{err}</Notice>}
          <button type="submit" data-testid="reset-password-submit" disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
            {busy && <Loader2 size={18} className="animate-spin" />} Save new password
          </button>
        </form>
      )}
    </AuthShell>
  );
}
