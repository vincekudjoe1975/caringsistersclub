import React from 'react';
import { Link } from 'react-router-dom';
import { org } from '../mock/mock';
import { Heart } from 'lucide-react';

export default function Logo({ variant = 'light', compact = false }) {
  const isLight = variant === 'light';
  return (
    <Link to="/" className="flex items-center gap-3 group" aria-label={`${org.name} home`}>
      <span
        className="relative flex items-center justify-center rounded-full shrink-0"
        style={{
          width: compact ? 42 : 52,
          height: compact ? 42 : 52,
          background: 'radial-gradient(circle at 30% 30%, #D14FA0, #3B0A2E)',
          boxShadow: '0 0 0 2px rgba(203,162,75,0.55), 0 0 22px -4px rgba(209,79,160,0.7)',
        }}
      >
        <Heart size={compact ? 20 : 24} className="text-white fill-white/90" strokeWidth={1.5} />
      </span>
      <span className="flex flex-col leading-none">
        <span
          className="font-serif font-bold tracking-wide"
          style={{ color: isLight ? '#F7EFE9' : '#3B0A2E', fontSize: compact ? 15 : 17 }}
        >
          {org.logoText.top}
          <span style={{ color: '#CBA24B' }} className="italic font-medium"> {org.logoText.sub}</span>
        </span>
        <span
          className="eyebrow mt-1"
          style={{ color: isLight ? 'rgba(247,239,233,0.7)' : 'rgba(59,10,46,0.6)', fontSize: 8.5 }}
        >
          {org.logoText.motto}
        </span>
      </span>
    </Link>
  );
}
