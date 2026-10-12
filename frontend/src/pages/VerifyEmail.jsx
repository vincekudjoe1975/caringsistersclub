import React, { useEffect, useRef, useState } from 'react';
import { Link, useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { AuthShell } from './ResetPassword';
import { Notice, apiError } from '../components/EmailAuth';
import { MailCheck, Loader2 } from 'lucide-react';

export default function VerifyEmail() {
  const [params] = useSearchParams();
  const { setUser } = useAuth();
  const navigate = useNavigate();
  const [err, setErr] = useState('');
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    api.post('/auth/verify-email', { token: params.get('token') || '' })
      .then(({ data }) => { setUser(data); navigate('/members?welcome=1', { replace: true }); })
      .catch((e) => setErr(apiError(e)));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AuthShell icon={MailCheck} title="Confirming your email" testid="verify-email-card">
      {err ? (
        <>
          <Notice kind="error" testid="verify-email-error">{err}</Notice>
          <p className="text-[13px] text-[#241019]/60 mt-5">Log in with your email and password to get a new link.</p>
          <Link to="/members" data-testid="verify-email-signin-link" className="inline-block mt-3 text-[14px] font-semibold text-[#B4247E]">Go to sign in</Link>
        </>
      ) : (
        <div data-testid="verify-email-loading" className="flex justify-center py-4"><Loader2 className="animate-spin text-[#CBA24B]" size={32} /></div>
      )}
    </AuthShell>
  );
}
