import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { QRCodeSVG } from 'qrcode.react';
import PageHero from '../components/PageHero';
import { Share, MoreHorizontal, Menu, MoreVertical, PlusSquare, Smartphone, Monitor, CheckCircle2, Download, Mail } from 'lucide-react';

const SITE = 'https://caringsistersclub.org';
const ua = () => window.navigator.userAgent;
export const isStandaloneApp = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

const detect = () => {
  const u = ua();
  const ios = /iphone|ipad|ipod/i.test(u) || (/macintosh/i.test(u) && navigator.maxTouchPoints > 1);
  if (ios) return /crios/i.test(u) ? 'ios-chrome' : /fxios/i.test(u) ? 'ios-firefox' : /edgios/i.test(u) ? 'ios-edge' : 'ios-safari';
  if (/android/i.test(u)) return /samsungbrowser/i.test(u) ? 'android-samsung' : /firefox/i.test(u) ? 'android-firefox' : 'android-chrome';
  return 'desktop';
};

const I = ({ icon: Icon }) => <span className="inline-flex align-middle mx-0.5 px-1.5 py-0.5 rounded-md bg-[#3B0A2E]/8 text-[#3B0A2E]"><Icon size={14} /></span>;

const GUIDES = {
  'ios-safari': { group: 'iPhone', label: 'Safari', steps: [
    <>Tap the <b>Share</b> button <I icon={Share} /> in the bar at the bottom of the screen. On iOS 26, tap <b>···</b> <I icon={MoreHorizontal} /> first, then <b>Share</b>.</>,
    <>Scroll down and tap <b>Add to Home Screen</b> <I icon={PlusSquare} />.</>,
    <>Make sure <b>Open as Web App</b> is switched on (if you see it), then tap <b>Add</b>.</>,
  ] },
  'ios-chrome': { group: 'iPhone', label: 'Chrome', steps: [
    <>Tap the <b>Share</b> button <I icon={Share} /> at the top right, next to the web address.</>,
    <>Tap <b>Add to Home Screen</b> <I icon={PlusSquare} />. If you don't see it, scroll to the bottom, tap <b>Edit Actions</b> and add it.</>,
    <>Tap <b>Add</b>.</>,
  ] },
  'ios-firefox': { group: 'iPhone', label: 'Firefox', steps: [
    <>Tap the menu button <I icon={Menu} /> at the bottom right.</>,
    <>Tap <b>Share</b> <I icon={Share} />, then <b>Add to Home Screen</b> <I icon={PlusSquare} />.</>,
    <>Tap <b>Add</b>.</>,
  ] },
  'ios-edge': { group: 'iPhone', label: 'Edge', steps: [
    <>Tap the menu button <I icon={MoreHorizontal} /> at the bottom.</>,
    <>Tap <b>Share</b> <I icon={Share} />, then <b>Add to Home Screen</b> <I icon={PlusSquare} />.</>,
    <>Tap <b>Add</b>.</>,
  ] },
  'android-chrome': { group: 'Android', label: 'Chrome', steps: [
    <>Tap the <b>Install app</b> button above, if you see it. Otherwise tap the menu <I icon={MoreVertical} /> at the top right.</>,
    <>Tap <b>Install app</b> or <b>Add to Home screen</b>.</>,
    <>Tap <b>Install</b>.</>,
  ] },
  'android-samsung': { group: 'Android', label: 'Samsung Internet', steps: [
    <>Tap the menu <I icon={Menu} /> at the bottom right.</>,
    <>Tap <b>Add page to</b>, then <b>Home screen</b>.</>,
    <>Tap <b>Add</b>.</>,
  ] },
  'android-firefox': { group: 'Android', label: 'Firefox', steps: [
    <>Tap the menu <I icon={MoreVertical} />.</>,
    <>Tap <b>Add app to Home screen</b> (or <b>Install</b>).</>,
    <>Tap <b>Add</b>.</>,
  ] },
  desktop: { group: 'Computer', label: 'Chrome or Edge', steps: [
    <>Click the <b>Install app</b> button above, or the install icon <I icon={Download} /> at the right end of the address bar.</>,
    <>Click <b>Install</b>. The Club opens in its own window.</>,
    <>Or scan the code below with your phone to install it there.</>,
  ] },
};
const GROUPS = ['iPhone', 'Android', 'Computer'];

export default function GetApp() {
  const [sel, setSel] = useState(detect);
  const [evt, setEvt] = useState(() => window.__cscInstallEvt || null);
  const [done, setDone] = useState(isStandaloneApp());
  useEffect(() => {
    const h = (e) => { e.preventDefault(); window.__cscInstallEvt = e; setEvt(e); };
    const ok = () => setDone(true);
    window.addEventListener('beforeinstallprompt', h);
    window.addEventListener('appinstalled', ok);
    return () => { window.removeEventListener('beforeinstallprompt', h); window.removeEventListener('appinstalled', ok); };
  }, []);
  const install = async () => { evt.prompt(); const { outcome } = await evt.userChoice; if (outcome === 'accepted') setDone(true); window.__cscInstallEvt = null; setEvt(null); };
  const g = GUIDES[sel];
  const group = g.group;

  return (
    <div data-testid="get-app-page">
      <PageHero kicker="Get the App" title="Caring Sisters Club on your phone" subtitle="Add the Club to your home screen for one-tap access to the member portal, gathering reminders and news alerts. It's free and takes 30 seconds." />
      <section className="bg-[#F7EFE9] py-14 md:py-20">
        <div className="max-w-5xl mx-auto px-5 lg:px-10 grid lg:grid-cols-[1fr_300px] gap-10 items-start">
          <div>
            {done ? (
              <div data-testid="get-app-installed" className="bg-white rounded-3xl p-7 border border-[#3B0A2E]/8 flex gap-4 items-start">
                <CheckCircle2 className="text-[#3c7a2f] shrink-0" size={28} />
                <div><p className="font-serif text-[22px] text-[#3B0A2E] font-semibold">You're all set!</p><p className="text-[14.5px] text-[#241019]/65 mt-1">The app is installed. Open it from your home screen and sign in.</p>
                  <Link to="/members" data-testid="get-app-open-portal" className="btn-magenta rounded-full px-6 py-3 font-semibold inline-block mt-4">Open the Member Portal</Link></div>
              </div>
            ) : (
              <>
                {evt && <button data-testid="get-app-install-btn" onClick={install} className="btn-magenta rounded-full px-7 py-3.5 font-semibold flex items-center gap-2 mb-8"><Download size={18} /> Install app</button>}
                <p className="text-[13px] font-semibold text-[#241019]/60 mb-2">Your device</p>
                <div className="flex flex-wrap gap-2 mb-4" role="tablist">
                  {GROUPS.map((gr) => (
                    <button key={gr} role="tab" aria-selected={group === gr} data-testid={`get-app-group-${gr.toLowerCase()}`} onClick={() => setSel(Object.keys(GUIDES).find((k) => GUIDES[k].group === gr))}
                      className={`rounded-full px-5 py-2 text-[14px] font-semibold flex items-center gap-2 transition-colors ${group === gr ? 'bg-[#3B0A2E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12 hover:border-[#B4247E]'}`}>
                      {gr === 'Computer' ? <Monitor size={15} /> : <Smartphone size={15} />} {gr}
                    </button>
                  ))}
                </div>
                {group !== 'Computer' && (
                  <div className="flex flex-wrap gap-2 mb-6">
                    {Object.entries(GUIDES).filter(([, v]) => v.group === group).map(([k, v]) => (
                      <button key={k} data-testid={`get-app-browser-${k}`} onClick={() => setSel(k)} className={`rounded-full px-4 py-1.5 text-[13px] font-semibold transition-colors ${sel === k ? 'bg-[#B4247E] text-white' : 'bg-white text-[#3B0A2E] border border-[#3B0A2E]/12'}`}>{v.label}</button>
                    ))}
                  </div>
                )}
                <div className="bg-white rounded-3xl p-6 md:p-8 border border-[#3B0A2E]/8" data-testid="get-app-steps">
                  <p className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-5">{group} · {g.label}</p>
                  <ol className="space-y-5">
                    {g.steps.map((st, i) => (
                      <li key={i} className="flex gap-4" style={{ animation: `fadeUp .45s ease ${i * 0.1}s both` }}>
                        <span className="w-8 h-8 rounded-full bg-[#B4247E] text-white font-bold text-[14px] flex items-center justify-center shrink-0">{i + 1}</span>
                        <p className="text-[15px] text-[#241019]/80 leading-relaxed pt-1">{st}</p>
                      </li>
                    ))}
                    <li className="flex gap-4">
                      <span className="w-8 h-8 rounded-full bg-[#CBA24B] text-[#241019] font-bold text-[14px] flex items-center justify-center shrink-0">{g.steps.length + 1}</span>
                      <p className="text-[15px] text-[#241019]/80 leading-relaxed pt-1">Open <b>Caring Sisters</b> from your home screen and sign in with <b><Mail size={14} className="inline -mt-0.5" /> Log in with Email</b>. Google members can set a password with "Forgot Password?".</p>
                    </li>
                  </ol>
                  {group === 'iPhone' && <p className="text-[12.5px] text-[#241019]/55 mt-6" data-testid="get-app-ios-note">Needs iOS 16.4 or newer to install from Chrome, Firefox or Edge. On older iPhones, open this page in Safari. Only install the app once, from one browser.</p>}
                </div>
              </>
            )}
          </div>
          <aside className="bg-white rounded-3xl p-6 border border-[#3B0A2E]/8 text-center lg:sticky lg:top-28" data-testid="get-app-qr">
            <p className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-1">On a computer?</p>
            <p className="text-[13px] text-[#241019]/60 mb-4">Scan with your phone's camera to open this page there.</p>
            <div className="inline-block p-3 rounded-2xl bg-[#F7EFE9]"><QRCodeSVG value={`${SITE}/app`} size={168} fgColor="#3B0A2E" bgColor="#F7EFE9" /></div>
            <p className="text-[12.5px] text-[#241019]/55 mt-3">caringsistersclub.org/app</p>
          </aside>
        </div>
      </section>
    </div>
  );
}
