import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { api } from '../lib/api';
import { useAuth } from '../context/AuthContext';
import { Loader2 } from 'lucide-react';

export default function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { setUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const hash = location.hash || window.location.hash || '';
    const match = hash.match(/session_id=([^&]+)/);
    const sessionId = match ? decodeURIComponent(match[1]) : null;

    if (!sessionId) {
      navigate('/login');
      return;
    }

    (async () => {
      try {
        const { data } = await api.post('/auth/session', { session_id: sessionId });
        setUser(data);
        window.history.replaceState(null, '', window.location.pathname);
        navigate('/admin', { state: { user: data } });
      } catch (e) {
        navigate('/login');
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="csc-hero-gradient min-h-screen flex flex-col items-center justify-center text-[#F7EFE9]">
      <Loader2 className="animate-spin text-[#CBA24B] mb-4" size={40} />
      <p className="font-serif text-[20px]">Signing you in…</p>
    </div>
  );
}
