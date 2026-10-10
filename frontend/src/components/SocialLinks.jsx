import React from 'react';
import { Instagram, Facebook, Youtube } from 'lucide-react';
import { org } from '../mock/mock';

const TikTok = ({ size = 16 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
    <path d="M16.6 5.82A4.28 4.28 0 0 1 15.54 3h-3.09v12.4a2.59 2.59 0 0 1-2.59 2.5c-1.42 0-2.6-1.16-2.6-2.6 0-1.72 1.66-3.01 3.37-2.48V9.66c-3.45-.46-6.47 2.22-6.47 5.64 0 3.33 2.76 5.7 5.69 5.7 3.14 0 5.69-2.55 5.69-5.7V9.01a7.35 7.35 0 0 0 4.3 1.38V7.3s-1.88.09-3.24-1.48z" />
  </svg>
);

const LINKS = [
  { Icon: Facebook, label: 'Facebook', key: 'facebook' },
  { Icon: Instagram, label: 'Instagram', key: 'instagram' },
  { Icon: Youtube, label: 'YouTube', key: 'youtube' },
  { Icon: TikTok, label: 'TikTok', key: 'tiktok' },
];

export const SocialLinks = ({ className = '', itemClassName = '' }) => (
  <div className={`flex items-center gap-3 ${className}`}>
    {LINKS.map(({ Icon, label, key }) => (
      <a key={key} href={org.social[key]} target="_blank" rel="noopener noreferrer" aria-label={label} title={label}
        data-testid={`social-${key}-link`}
        className={`w-9 h-9 rounded-full flex items-center justify-center transition-colors ${itemClassName}`}>
        <Icon size={16} />
      </a>
    ))}
  </div>
);
