import React, { useState } from 'react';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { Mail, Eye, EyeOff, Loader2, CheckCircle2, AlertCircle } from 'lucide-react';

export const apiError = (e) => {
  const d = e?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (Array.isArray(d)) return d.map((x) => x?.msg).filter(Boolean).join(' ') || 'Please check your details.';
  return 'Something went wrong. Please try again.';
};

export const pwOk = (pw) => pw.length >= 8 && /[A-Za-z]/.test(pw) && /\d/.test(pw);

const inputCls = 'w-full rounded-xl border border-[#3B0A2E]/15 bg-[#FBF7F4] px-4 py-3 text-[14.5px] text-[#241019] placeholder:text-[#241019]/40 focus:outline-none focus:border-[#B4247E] focus:ring-2 focus:ring-[#B4247E]/15 transition-colors';

export const Field = ({ label, testid, ...props }) => (
  <label className="block text-left">
    <span className="block text-[12.5px] font-semibold text-[#3B0A2E] mb-1.5">{label}</span>
    <input data-testid={testid} className={inputCls} {...props} />
  </label>
);

export const PasswordField = ({ label = 'Password', testid, value, onChange, autoComplete }) => {
  const [show, setShow] = useState(false);
  return (
    <label className="block text-left">
      <span className="block text-[12.5px] font-semibold text-[#3B0A2E] mb-1.5">{label}</span>
      <span className="relative block">
        <input data-testid={testid} type={show ? 'text' : 'password'} required value={value} onChange={onChange} autoComplete={autoComplete} className={`${inputCls} pr-11`} />
        <button type="button" data-testid={`${testid}-toggle`} aria-label={show ? 'Hide password' : 'Show password'} onClick={() => setShow((s) => !s)} className="absolute right-3 top-1/2 -translate-y-1/2 text-[#241019]/45 hover:text-[#B4247E] transition-colors">
          {show ? <EyeOff size={17} /> : <Eye size={17} />}
        </button>
      </span>
    </label>
  );
};

export const Notice = ({ kind, children, testid }) => (
  <div data-testid={testid} role={kind === 'error' ? 'alert' : 'status'} className={`flex items-start gap-2 text-left rounded-xl px-3.5 py-3 text-[13px] leading-snug ${kind === 'error' ? 'bg-[#FDECEF] text-[#9B1C3A]' : 'bg-[#EEF7EF] text-[#245C32]'}`}>
    {kind === 'error' ? <AlertCircle size={16} className="shrink-0 mt-0.5" /> : <CheckCircle2 size={16} className="shrink-0 mt-0.5" />}<span>{children}</span>
  </div>
);

const TITLES = { login: 'Log in with Email', signup: 'Sign up with Email', forgot: 'Forgot Password?' };

export function EmailAuth({ onBack }) {
  const { setUser } = useAuth();
  const [mode, setMode] = useState('login');
  const [f, setF] = useState({ name: '', email: '', password: '', confirm: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');
  const [unverified, setUnverified] = useState(false);
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));
  const go = (m) => { setMode(m); setErr(''); setOk(''); setUnverified(false); };

  const submit = async (e) => {
    e.preventDefault();
    setErr(''); setOk(''); setUnverified(false);
    if (mode === 'signup' && !pwOk(f.password)) return setErr('Password must be at least 8 characters and include at least 1 letter and 1 number.');
    if (mode === 'signup' && f.password !== f.confirm) return setErr("Passwords don't match.");
    setBusy(true);
    try {
      if (mode === 'login') {
        const { data } = await api.post('/auth/login', { email: f.email, password: f.password });
        setUser(data);
      } else if (mode === 'signup') {
        const { data } = await api.post('/auth/signup', { name: f.name, email: f.email, password: f.password });
        setOk(data.message); setF((s) => ({ ...s, password: '', confirm: '' }));
      } else {
        const { data } = await api.post('/auth/reset-password-request', { email: f.email });
        setOk(data.message);
      }
    } catch (e2) {
      setErr(apiError(e2));
      setUnverified(e2?.response?.status === 403);
    } finally { setBusy(false); }
  };

  const resend = async () => {
    try { const { data } = await api.post('/auth/resend-verification', { email: f.email }); setErr(''); setUnverified(false); setOk(data.message); }
    catch (e2) { setErr(apiError(e2)); }
  };

  return (
    <form data-testid="email-auth-form" onSubmit={submit} className="space-y-4 text-left" noValidate>
      <h2 data-testid="email-auth-title" className="font-serif text-[20px] text-[#3B0A2E] font-semibold text-center">{TITLES[mode]}</h2>
      {mode === 'signup' && <Field label="Your name" testid="email-auth-name" value={f.name} onChange={set('name')} autoComplete="name" placeholder="First and last name" />}
      <Field label="Email address" testid="email-auth-email" type="email" required value={f.email} onChange={set('email')} autoComplete="email" placeholder="name@example.com" />
      {mode !== 'forgot' && <PasswordField testid="email-auth-password" value={f.password} onChange={set('password')} autoComplete={mode === 'signup' ? 'new-password' : 'current-password'} />}
      {mode === 'signup' && <>
        <p data-testid="email-auth-pw-rules" className={`text-[12px] -mt-2 ${f.password && !pwOk(f.password) ? 'text-[#9B1C3A]' : 'text-[#241019]/55'}`}>At least 8 characters, with at least 1 letter and 1 number.</p>
        <PasswordField label="Confirm password" testid="email-auth-confirm" value={f.confirm} onChange={set('confirm')} autoComplete="new-password" />
      </>}
      {mode === 'login' && <button type="button" data-testid="email-auth-forgot-link" onClick={() => go('forgot')} className="text-[13px] font-semibold text-[#B4247E] hover:underline">Forgot Password?</button>}
      {err && <Notice kind="error" testid="email-auth-error">{err}</Notice>}
      {unverified && <button type="button" data-testid="email-auth-resend-btn" onClick={resend} className="text-[13px] font-semibold text-[#B4247E] hover:underline">Resend confirmation email</button>}
      {ok && <Notice kind="ok" testid="email-auth-success">{ok}</Notice>}
      <button type="submit" data-testid="email-auth-submit" disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 size={18} className="animate-spin" /> : <Mail size={18} />}
        {mode === 'login' ? 'Log in' : mode === 'signup' ? 'Create account' : 'Send reset link'}
      </button>
      <div className="text-center text-[13px] text-[#241019]/60 space-y-1.5">
        {mode === 'login' && <p>New here? <button type="button" data-testid="email-auth-to-signup" onClick={() => go('signup')} className="font-semibold text-[#B4247E] hover:underline">Sign up with Email</button></p>}
        {mode !== 'login' && <p>Already have an account? <button type="button" data-testid="email-auth-to-login" onClick={() => go('login')} className="font-semibold text-[#B4247E] hover:underline">Log in with Email</button></p>}
        <p><button type="button" data-testid="email-auth-back" onClick={onBack} className="font-semibold text-[#3B0A2E]/70 hover:text-[#B4247E]">Back to all sign-in options</button></p>
      </div>
    </form>
  );
}

export function SignInOptions({ onGoogle, googleTestid }) {
  const [email, setEmail] = useState(false);
  if (email) return <EmailAuth onBack={() => setEmail(false)} />;
  return (
    <div className="space-y-3">
      <button data-testid={googleTestid} onClick={onGoogle} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2">
        <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#fff" d="M44.5 20H24v8.5h11.8C34.7 33.9 30.1 37 24 37c-7.2 0-13-5.8-13-13s5.8-13 13-13c3.1 0 5.9 1.1 8.1 2.9l6.4-6.4C34.6 4.1 29.6 2 24 2 11.8 2 2 11.8 2 24s9.8 22 22 22c11 0 21-8 21-22 0-1.3-.2-2.7-.5-4z" /></svg>
        Continue with Google
      </button>
      <div className="flex items-center gap-3 py-1 text-[11.5px] uppercase tracking-[0.14em] text-[#241019]/40"><span className="h-px flex-1 bg-[#241019]/10" />or<span className="h-px flex-1 bg-[#241019]/10" /></div>
      <button data-testid="email-login-open-btn" onClick={() => setEmail(true)} className="rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 border-2 border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] transition-colors">
        <Mail size={18} /> Log in or Sign up with Email
      </button>
      <p className="text-[12px] text-[#241019]/50 pt-1">No Google account? No problem: use any email address.</p>
    </div>
  );
}
