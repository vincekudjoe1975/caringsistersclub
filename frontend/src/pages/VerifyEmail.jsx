import React, { useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from './ResetPassword';
import { Notice, apiError } from '../components/EmailAuth';
import { MailCheck, Loader2 } from 'lucide-react';

// Confirm on tap (not on page load) so email link-scanners can't use up the one-time link.
export default function VerifyEmail() {
  const [params] = useSearchParams();
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [err, setErr] = useState('');
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const confirm = async () => {
    setBusy(true); setErr('');
    try {
      const { data } = await api.post('/auth/verify-email', { token: params.get('token') || '' });
      setUser(data); navigate('/members?welcome=1', { replace: true });
    } catch (e) { setErr(apiError(e)); setDone(e?.response?.status === 409); }
    finally { setBusy(false); }
  };

  return (
    <AuthShell icon={MailCheck} title="Confirm your email" testid="verify-email-card">
      {err ? (
        <>
          <Notice kind={done ? 'ok' : 'error'} testid="verify-email-error">{err}</Notice>
          {!done && <p className="text-[13px] text-[#241019]/60 mt-5">Log in with your email and password to get a new link.</p>}
          <Link to="/members" data-testid="verify-email-signin-link" className="btn-magenta rounded-full w-full py-3.5 mt-5 font-semibold flex items-center justify-center">Go to sign in</Link>
        </>
      ) : (
        <>
          <p className="text-[14px] text-[#241019]/65 mb-6">One last step: tap below to confirm your email and finish creating your account.</p>
          <button data-testid="verify-email-confirm-btn" onClick={confirm} disabled={busy} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
            {busy ? <Loader2 size={18} className="animate-spin" /> : <MailCheck size={18} />} Confirm my email
          </button>
        </>
      )}
    </AuthShell>
  );
}
