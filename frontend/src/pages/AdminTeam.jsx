import React, { useEffect, useState, useCallback } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, UserPlus, Mail, X } from 'lucide-react';
import { TeamList } from '../components/admin/TeamList';
import { MergeAccounts } from '../components/MergeAccounts';

export default function AdminTeam({ currentUserId }) {
  const { toast } = useToast();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [newEmail, setNewEmail] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/admin/team');
      setData(res.data);
    } catch (e) {
      console.error('AdminTeam: failed to load', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const allow = async (e) => {
    e.preventDefault();
    const email = newEmail.trim().toLowerCase();
    if (!email || !email.includes('@')) { toast({ title: 'Enter a valid email', variant: 'destructive' }); return; }
    try {
      await api.post('/admin/team/allow', { email });
      toast({ title: 'Email approved', description: `${email} can now access the admin.` });
      setNewEmail('');
      load();
    } catch (err) {
      toast({ title: 'Failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    }
  };

  const change = async (u, to) => {
    try {
      if (to === 'member') await api.post(`/admin/team/${u.user_id}/make-member`);
      else await api.post(`/admin/team/${u.user_id}/role`, { role: 'admin' });
      toast({ title: to === 'member' ? 'Changed to member' : 'Admin access granted', description: to === 'member' ? `${u.name || u.email} can no longer open Admin. She now appears under Members.` : undefined });
      load();
    } catch (err) {
      toast({ title: 'Failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    }
  };

  const removeAllowed = async (email) => {
    try {
      await api.post('/admin/team/revoke-email', { email });
      load();
    } catch (e) {
      console.error('AdminTeam: revoke failed', e);
    }
  };

  if (loading && !data) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  }

  const users = data?.users || [];
  const allowed = data?.allowed_emails || [];

  return (
    <div className="grid lg:grid-cols-[1fr_320px] gap-8 items-start">
      <TeamList users={users} me={currentUserId} onConfirm={change} />

      {/* Pre-approve */}
      <div className="space-y-5">
        <form onSubmit={allow} className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
          <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-2 flex items-center gap-2"><UserPlus size={18} className="text-[#B4247E]" /> Pre-approve an email</h3>
          <p className="text-[12.5px] text-[#241019]/60 mb-4">They'll get admin access the first time they sign in with Google, or after setting a password with "Forgot Password?" on the staff login.</p>
          <input type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)} placeholder="name@example.com"
            className="w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E] mb-3" />
          <button type="submit" className="btn-magenta rounded-full w-full py-2.5 font-semibold text-[14px]">Approve Email</button>
        </form>

        {allowed.length > 0 && (
          <div className="bg-white rounded-2xl p-6 border border-[#3B0A2E]/8">
            <h4 className="eyebrow text-[#B4247E] mb-3">Approved Emails</h4>
            <ul className="space-y-2">
              {allowed.map((em) => (
                <li key={em} className="flex items-center justify-between text-[13px] text-[#3B0A2E]">
                  <span className="flex items-center gap-2 truncate"><Mail size={14} className="text-[#241019]/40 shrink-0" /> {em}</span>
                  <button onClick={() => removeAllowed(em)} className="text-[#241019]/40 hover:text-red-500 p-1"><X size={15} /></button>
                </li>
              ))}
            </ul>
          </div>
        )}
        <MergeAccounts toast={toast} onDone={load} />
      </div>
    </div>
  );
}
