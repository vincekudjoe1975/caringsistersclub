import React, { useEffect, useState, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../lib/api';
import { Loader2, LogIn, Megaphone, MessagesSquare, Users, ScrollText, UserCircle, LogOut, Clock, ShieldCheck, Vote, Wallet, FileText, Star, HandHeart } from 'lucide-react';
import { MemberApply } from '../components/members/MemberApply';
import { Announcements } from '../components/members/Announcements';
import { Discussion } from '../components/members/Discussion';
import { Directory } from '../components/members/Directory';
import { Bylaws } from '../components/members/Bylaws';
import { MyProfile } from '../components/members/MyProfile';
import { Ballots } from '../components/members/Ballots';
import { Standing } from '../components/members/Standing';
import { Minutes } from '../components/members/Minutes';
import { SpotlightArchive, PrayerBoard } from '../components/members/Phase6';

const TABS = [
  { k: 'news', l: 'Announcements', icon: Megaphone, C: Announcements },
  { k: 'talk', l: 'Discussion', icon: MessagesSquare, C: Discussion },
  { k: 'prayer', l: 'Prayer', icon: HandHeart, C: PrayerBoard },
  { k: 'votes', l: 'Votes', icon: Vote, C: Ballots },
  { k: 'dues', l: 'My Dues', icon: Wallet, C: Standing },
  { k: 'people', l: 'Directory', icon: Users, C: Directory },
  { k: 'spotlights', l: 'Spotlights', icon: Star, C: SpotlightArchive },
  { k: 'minutes', l: 'Minutes', icon: FileText, C: Minutes },
  { k: 'bylaws', l: 'Bylaws', icon: ScrollText, C: Bylaws },
  { k: 'me', l: 'My Profile', icon: UserCircle, C: MyProfile },
];

const Shell = ({ children }) => (
  <section className="csc-hero-gradient min-h-screen pt-[120px] pb-20 px-5 relative overflow-hidden">
    <div className="absolute -right-24 -top-24 w-96 h-96 rounded-full opacity-30" style={{ background: 'radial-gradient(circle,#D14FA0,transparent 70%)' }} />
    <div className="relative max-w-6xl mx-auto">{children}</div>
  </section>
);

const Card = ({ icon: Icon, title, children, testid }) => (
  <div data-testid={testid} className="bg-white rounded-3xl p-10 max-w-lg mx-auto text-center" style={{ boxShadow: '0 40px 80px -30px rgba(0,0,0,0.5)' }}>
    <span className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-6" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}><Icon size={30} className="text-white" /></span>
    <h1 className="font-serif text-[28px] text-[#3B0A2E] font-semibold mb-3">{title}</h1>
    {children}
  </div>
);

function MemberLogin() {
  const login = () => {
    // REMINDER: DO NOT HARDCODE THE URL, OR ADD ANY FALLBACKS OR REDIRECT URLS, THIS BREAKS THE AUTH
    const redirectUrl = window.location.origin + '/members';
    window.location.href = `https://auth.emergentagent.com/?redirect=${encodeURIComponent(redirectUrl)}`;
  };
  return (
    <Card icon={LogIn} title="Member Portal" testid="member-login-card">
      <p className="text-[#241019]/65 text-[14.5px] mb-8">Sign in to read our bylaws, meet your sisters, and join the conversation.</p>
      <button data-testid="member-login-btn" onClick={login} className="btn-magenta rounded-full w-full py-3.5 font-semibold flex items-center justify-center gap-2"><LogIn size={18} /> Continue with Google</button>
      <p className="text-[13px] text-[#241019]/55 mt-6">Not a member yet? <Link to="/membership" data-testid="member-learn-link" className="text-[#B4247E] font-semibold">Learn how to join</Link></p>
    </Card>
  );
}

function Portal({ me, onChange }) {
  const [tab, setTab] = useState(() => (window.location.search.includes('dues_session') ? 'dues' : sessionStorage.getItem('csc_member_tab') || 'news'));
  const pick = (k) => { sessionStorage.setItem('csc_member_tab', k); setTab(k); };
  const { logout } = useAuth();
  const Current = (TABS.find((t) => t.k === tab) || TABS[0]).C;
  return (
    <>
      <div className="flex flex-wrap items-end justify-between gap-4 mb-8">
        <div>
          <p className="eyebrow text-[#CBA24B] mb-3">Members only</p>
          <h1 data-testid="portal-welcome" className="font-serif text-[#F7EFE9] text-4xl sm:text-5xl font-semibold">Welcome, {(me.name || 'Sister').split(' ')[0]}</h1>
        </div>
        <div className="flex gap-2">
          {me.is_admin && <Link to="/admin" data-testid="portal-admin-link" className="rounded-full px-5 py-2.5 text-[13px] font-semibold text-[#F7EFE9] border border-white/25 flex items-center gap-1.5 hover:bg-white/10 transition-colors"><ShieldCheck size={14} /> Staff admin</Link>}
          <button data-testid="portal-logout-btn" onClick={logout} className="rounded-full px-5 py-2.5 text-[13px] font-semibold text-[#F7EFE9] border border-white/25 flex items-center gap-1.5 hover:bg-white/10 transition-colors"><LogOut size={14} /> Sign out</button>
        </div>
      </div>
      <div className="inline-flex flex-wrap gap-1 p-1.5 rounded-full mb-8 bg-white/10 backdrop-blur-md border border-white/15">
        {TABS.map(({ k, l, icon: Icon }) => (
          <button key={k} data-testid={`portal-tab-${k}`} onClick={() => pick(k)}
            className={`px-5 py-2 rounded-full text-[14px] font-semibold flex items-center gap-2 transition-colors ${tab === k ? 'bg-[#F7EFE9] text-[#3B0A2E]' : 'text-[#F7EFE9]/85 hover:text-white'}`}>
            <Icon size={16} /> {l}
          </button>
        ))}
      </div>
      <div className="bg-[#F7EFE9] rounded-3xl p-6 md:p-10"><Current me={me} onChange={onChange} /></div>
    </>
  );
}

export default function Members() {
  const { user } = useAuth();
  const [me, setMe] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await api.get('/members/me'); setMe(data); } catch { setMe(false); }
  }, []);
  useEffect(() => { if (user) load(); }, [user, load]);

  if (user === null || (user && me === null)) return <Shell><div className="flex justify-center py-32"><Loader2 className="animate-spin text-[#CBA24B]" size={36} /></div></Shell>;
  if (!user || me === false) return <Shell><MemberLogin /></Shell>;
  if (me.status === 'active') return <Shell><Portal me={me} onChange={load} /></Shell>;
  if (me.status === 'applied') return <Shell><Card icon={Clock} title="Application received" testid="member-pending-card"><p className="text-[#241019]/65 text-[14.5px]">Thank you, {(me.name || '').split(' ')[0]}. Our membership team will review your application and email you once you're approved.</p></Card></Shell>;
  if (me.status === 'declined' || me.status === 'suspended' || me.status === 'ended') return <Shell><Card icon={Clock} title="Portal access paused" testid="member-paused-card"><p className="text-[#241019]/65 text-[14.5px]">Your member access isn't active right now. Please <Link to="/contact" className="text-[#B4247E] font-semibold">contact us</Link> if you have questions.</p></Card></Shell>;
  return <Shell><MemberApply me={me} onDone={load} /></Shell>;
}
