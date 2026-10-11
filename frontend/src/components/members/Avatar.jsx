import React, { useState } from 'react';
import { initials } from './fmt';

export function Avatar({ name, src, size = 40 }) {
  const [broken, setBroken] = useState(false);
  if (src && !broken) return <img src={src.startsWith('/api') ? `${process.env.REACT_APP_BACKEND_URL}${src}` : src} alt="" referrerPolicy="no-referrer" onError={() => setBroken(true)} className="rounded-full object-cover shrink-0" style={{ width: size, height: size }} />;
  return (
    <span className="rounded-full shrink-0 flex items-center justify-center text-white font-semibold" style={{ width: size, height: size, fontSize: size * 0.36, background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
      {initials(name)}
    </span>
  );
}
