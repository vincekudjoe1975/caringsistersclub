import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Switch } from './ui/switch';
import { ShieldCheck } from 'lucide-react';

export function StaffCodeToggle() {
  const { toast } = useToast();
  const [st, setSt] = useState(null);
  useEffect(() => { api.get('/auth/staff-code/pref').then(({ data }) => setSt(data)).catch(() => {}); }, []);
  if (!st) return null;
  const change = async (enabled) => {
    try {
      await api.put('/auth/staff-code/pref', { enabled });
      setSt({ ...st, enabled });
      toast({ title: enabled ? 'Email code turned on' : 'Email code turned off', description: enabled ? 'From your next sign-in, Admin will ask for a code sent to your email.' : 'You will sign in to Admin as before.' });
    } catch (e) { toast({ title: 'Could not update', description: e?.response?.data?.detail, variant: 'destructive' }); }
  };
  return (
    <div data-testid="staff-code-toggle-card" className="mb-6 bg-white rounded-2xl p-5 border border-[#3B0A2E]/8 flex items-start gap-4">
      <span className="w-10 h-10 shrink-0 rounded-xl bg-[#F7EFE9] text-[#B4247E] flex items-center justify-center"><ShieldCheck size={19} /></span>
      <div className="flex-1 min-w-0">
        <p className="font-serif text-[17px] text-[#3B0A2E] font-semibold">Ask me for an email code every time I sign in</p>
        <p data-testid="staff-code-toggle-status" className="text-[13px] text-[#241019]/60 mt-0.5">Your setting only. After your password or Google sign-in, Admin will ask for a 6-digit code sent to {st.email}.</p>
      </div>
      <Switch data-testid="staff-code-toggle" checked={st.enabled} onCheckedChange={change} aria-label="Require an email code for Admin sign-in" />
    </div>
  );
}
