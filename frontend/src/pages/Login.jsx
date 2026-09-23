import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Logo from '../components/Logo';
import { LogIn, ShieldCheck, Loader2 } from 'lucide-react';

export default function Login() {
  const { user } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate('/admin');
  }, [user, navigate]);

  const handleLogin = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/admin';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };

  if (user === null) {
    return (
      <div className="csc-hero-gradient min-h-screen flex items-center justify-center">
        <Loader2 className="animate-spin text-[#CBA24B]" size={36} />
      </div>
    );
  }

  return (
    <div className="csc-hero-gradient min-h-screen flex items-center justify-center px-5 relative overflow-hidden">
      <div className="absolute -right-24 -top-24 w-96 h-96 rounded-full opacity-30" style={{ background: 'radial-gradient(circle,#D14FA0,transparent 70%)' }} />
      <div className="absolute -left-16 bottom-0 w-72 h-72 rounded-full opacity-20" style={{ background: 'radial-gradient(circle,#CBA24B,transparent 70%)' }} />
      <div className="relative bg-white rounded-3xl p-10 w-full max-w-md text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
        <div className="flex justify-center mb-6">
          <Logo variant="dark" />
        </div>
        <span className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
          <ShieldCheck size={30} className="text-white" />
        </span>
        <h1 className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-2">Admin Portal</h1>
        <p className="text-[#241019]/65 text-[14.5px] mb-8">
          Sign in to manage gallery photos, leadership, events, and financial documents.
        </p>
        <button onClick={handleLogin} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2">
          <LogIn size={18} /> Continue with Google
        </button>
        <p className="text-[12px] text-[#241019]/45 mt-6">Secure sign-in powered by Emergent.</p>
      </div>
    </div>
  );
}
