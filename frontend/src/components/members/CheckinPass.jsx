import React, { useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { QrCode, X, WifiOff } from 'lucide-react';
import { api } from '../../lib/api';

export const CODE_KEY = 'csc_checkin_code';

export const useCheckinCode = (fetchIt = true) => {
  const [code, setCode] = useState(() => localStorage.getItem(CODE_KEY) || '');
  useEffect(() => {
    if (!fetchIt) return;
    api.get('/members/checkin-code').then(({ data }) => { localStorage.setItem(CODE_KEY, data.code); setCode(data.code); }).catch(() => {});
  }, [fetchIt]);
  return code;
};

export const PassModal = ({ code, onClose, offline }) => (
  <div data-testid="checkin-pass-modal" className="fixed inset-0 z-[120] bg-[#1d0517]/85 backdrop-blur-md flex items-center justify-center p-5" onClick={onClose}>
    <div className="bg-white rounded-3xl p-7 w-full max-w-sm text-center relative" onClick={(e) => e.stopPropagation()}>
      <button data-testid="checkin-pass-close" onClick={onClose} aria-label="Close" className="absolute top-3 right-3 w-11 h-11 flex items-center justify-center text-[#3B0A2E]/60"><X size={20} /></button>
      <p className="font-serif text-[24px] text-[#3B0A2E] font-semibold">My check-in code</p>
      <p className="text-[14px] text-[#241019]/65 mt-1 mb-5">Show this to staff at the door.</p>
      <div className="inline-block p-3 rounded-2xl border border-[#3B0A2E]/10"><QRCodeSVG data-testid="checkin-pass-qr" value={code} size={240} fgColor="#3B0A2E" /></div>
      {offline && <p data-testid="checkin-pass-offline" className="text-[13px] text-[#241019]/60 mt-4 flex items-center justify-center gap-1.5"><WifiOff size={14} /> Saved on this phone, works without signal</p>}
    </div>
  </div>
);

export const CheckinPassButton = () => {
  const code = useCheckinCode();
  const [open, setOpen] = useState(false);
  if (!code) return null;
  return (
    <>
      <button data-testid="portal-checkin-btn" onClick={() => setOpen(true)} className="rounded-full px-5 py-2.5 text-[13px] font-semibold bg-[#CBA24B] text-[#3B0A2E] flex items-center gap-1.5 hover:brightness-105 transition-[filter]"><QrCode size={14} /> My check-in code</button>
      {open && <PassModal code={code} onClose={() => setOpen(false)} />}
    </>
  );
};

export const OfflinePass = () => {
  const code = localStorage.getItem(CODE_KEY);
  const [open, setOpen] = useState(false);
  if (!code || navigator.onLine) return null;
  return (
    <div data-testid="offline-pass" className="max-w-lg mx-auto mt-6 text-center">
      <button data-testid="offline-pass-btn" onClick={() => setOpen(true)} className="rounded-full px-6 py-3.5 font-semibold bg-[#CBA24B] text-[#3B0A2E] inline-flex items-center gap-2"><QrCode size={18} /> Show my saved check-in code</button>
      {open && <PassModal code={code} offline onClose={() => setOpen(false)} />}
    </div>
  );
};
