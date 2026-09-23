import React from 'react';
import { Link } from 'react-router-dom';
import { org } from '../mock/mock';
import logoImg from '../assets/team/logo.png';

export default function Logo({ variant = 'light', compact = false }) {
  const isLight = variant === 'light';
  const size = compact ? 44 : 54;
  return (
    <Link to="/" className="flex items-center gap-3 group" aria-label={`${org.name} home`}>
      <img
        src={logoImg}
        alt="Caring Sisters Club logo"
        className="rounded-full object-cover shrink-0"
        style={{
          width: size,
          height: size,
          boxShadow: '0 0 0 1.5px rgba(203,162,75,0.5), 0 0 18px -4px rgba(209,79,160,0.6)',
        }}
      />
      <span className="hidden sm:flex flex-col leading-none">
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
