import React, { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import { useToast } from '../../hooks/use-toast';
import { KeyRound, Loader2, Mail } from 'lucide-react';
import { PasswordField, Notice, apiError, pwOk } from '../EmailAuth';

export function PasswordCard() {
  const { toast } = useToast();
  const [st, setSt] = useState(null);
  const [f, setF] = useState({ current: '', pw: '', confirm: '' });
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');
  const load = () => api.get('/auth/password-status').then(({ data }) => setSt(data)).catch(() => {});
  useEffect(() => { load(); }, []);
  if (!st) return null;
  const has = st.has_password;
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e.target.value }));

  const save = async () => {
    setErr('');
    if (has && !f.current) return setErr('Please enter your current password.');
    if (!pwOk(f.pw)) return setErr('Password must be at least 8 characters and include at least 1 letter and 1 number.');
    if (f.pw !== f.confirm) return setErr("Passwords don't match.");
    setBusy(true);
    try {
      const { data } = await api.post('/auth/set-password', { password: f.pw, current_password: f.current });
      toast({ title: has ? 'Password changed' : 'Password added', description: data.message });
      setF({ current: '', pw: '', confirm: '' }); load();
    } catch (e) { setErr(apiError(e)); }
    finally { setBusy(false); }
  };
  const emailLink = async () => {
    try { await api.post('/auth/reset-password-request', { email: st.email }); toast({ title: 'Check your inbox', description: `We sent a link to ${st.email} to set your password.` }); }
    catch (e) { setErr(apiError(e)); }
  };

  return (
    <div data-testid="password-card" onKeyDown={(e) => { if (e.key === 'Enter' && e.target.tagName === 'INPUT') { e.preventDefault(); save(); } }} className="mt-8 rounded-2xl bg-white border border-[#3B0A2E]/10 p-5 sm:p-6">
      <p className="flex items-center gap-2 font-serif text-[18px] text-[#3B0A2E] font-semibold"><KeyRound size={17} className="text-[#B4247E]" /> {has ? 'Change password' : 'Add a password'}</p>
      <p data-testid="password-card-status" className="text-[13px] text-[#241019]/60 mt-1 mb-4">
        {has ? 'You can sign in with your email and password' : 'You sign in with Google. Add a password so you can also sign in with your email and password'}{(st.providers || []).includes('google') && has ? ' or with Google.' : '.'}
      </p>
      <div className="space-y-3">
        {has && <PasswordField label="Current password" testid="password-current" value={f.current} onChange={set('current')} autoComplete="current-password" />}
        <PasswordField label="New password" testid="password-new" value={f.pw} onChange={set('pw')} autoComplete="new-password" />
        <p className="text-[12px] text-[#241019]/55 -mt-1">At least 8 characters, with at least 1 letter and 1 number.</p>
        <PasswordField label="Confirm new password" testid="password-confirm" value={f.confirm} onChange={set('confirm')} autoComplete="new-password" />
        {err && <Notice kind="error" testid="password-error">{err}</Notice>}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <button type="button" data-testid="password-save-btn" disabled={busy} onClick={save} className="btn-magenta rounded-full px-6 py-2.5 font-semibold flex items-center gap-2 disabled:opacity-60">
            {busy ? <Loader2 size={15} className="animate-spin" /> : <KeyRound size={15} />} {has ? 'Change password' : 'Add password'}
          </button>
          <button type="button" data-testid="password-email-link-btn" onClick={emailLink} className="text-[13.5px] font-semibold text-[#B4247E] flex items-center gap-1.5 hover:underline">
            <Mail size={14} /> {has ? 'Forgot it? Email me a reset link' : 'Email me a link instead'}
          </button>
        </div>
      </div>
    </div>
  );
}
