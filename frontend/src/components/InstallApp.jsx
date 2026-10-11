import React, { useEffect, useState } from 'react';
import { Smartphone, X, Share } from 'lucide-react';
import { api } from '../lib/api';

const KEY = 'csc_installed';
const HIDE = 'csc_install_hidden';
const isStandalone = () => window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
const isIOS = () => /iphone|ipad|ipod/i.test(window.navigator.userAgent);
const markInstalled = () => { localStorage.setItem(KEY, '1'); api.post('/members/app-installed').catch(() => {}); };

export const InstallApp = ({ light = false }) => {
  const [evt, setEvt] = useState(null);
  const [show, setShow] = useState(false);
  useEffect(() => {
    if (isStandalone()) { markInstalled(); return undefined; }
    if (localStorage.getItem(KEY) || sessionStorage.getItem(HIDE) || window.innerWidth >= 768) return undefined;
    let alive = true;
    const h = (e) => { e.preventDefault(); setEvt(e); };
    const done = () => { markInstalled(); setShow(false); };
    window.addEventListener('beforeinstallprompt', h);
    window.addEventListener('appinstalled', done);
    api.get('/members/me').then(({ data }) => {
      if (data.app_installed) localStorage.setItem(KEY, '1');
      else if (alive) setShow(true);
    }).catch(() => { if (alive) setShow(true); });
    return () => { alive = false; window.removeEventListener('beforeinstallprompt', h); window.removeEventListener('appinstalled', done); };
  }, []);
  if (!show || (!evt && !isIOS())) return null;
  const close = () => { sessionStorage.setItem(HIDE, '1'); setShow(false); };
  const install = async () => { evt.prompt(); const { outcome } = await evt.userChoice; if (outcome === 'accepted') { markInstalled(); setShow(false); } };
  return (
    <div data-testid="install-app-banner" className={`mb-6 rounded-2xl p-4 flex items-start gap-3 border ${light ? 'bg-white border-[#3B0A2E]/10 text-[#3B0A2E]' : 'bg-white/10 backdrop-blur-md border-white/15 text-[#F7EFE9]'}`}>
      <img src="/icon-192.png" alt="" className="w-11 h-11 rounded-xl shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="font-semibold text-[15px] flex items-center gap-1.5"><Smartphone size={15} /> Add the Club to your home screen</p>
        {evt ? (
          <button data-testid="install-app-btn" onClick={install} className="btn-magenta rounded-full px-5 py-2 mt-2.5 text-[14px] font-semibold">Install app</button>
        ) : (
          <p data-testid="install-app-ios-tip" className="text-[13.5px] opacity-80 mt-1">Tap <Share size={13} className="inline -mt-0.5" /> Share, then “Add to Home Screen”.</p>
        )}
      </div>
      <button data-testid="install-app-dismiss" onClick={close} aria-label="Hide for now" className="w-10 h-10 -m-2 flex items-center justify-center opacity-70 hover:opacity-100"><X size={18} /></button>
    </div>
  );
};
