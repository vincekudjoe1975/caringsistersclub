import React from 'react';
import { Link } from 'react-router-dom';
import { org, nav } from '../mock/mock';
import Logo from './Logo';
import { Instagram, Facebook, Linkedin, Youtube, MapPin, Phone, Mail } from 'lucide-react';

export default function Footer() {
  const legal = [
    { label: 'Privacy Policy', to: '/privacy-policy' },
    { label: 'Terms of Service', to: '/terms-of-service' },
    { label: 'Accessibility (ADA)', to: '/accessibility' },
    { label: 'Donor Privacy Policy', to: '/donor-privacy' },
  ];
  return (
    <footer style={{ background: '#29061F', color: '#F7EFE9' }}>
      <div className="max-w-7xl mx-auto px-5 lg:px-8 pt-16 pb-8">
        <div className="grid md:grid-cols-4 gap-10">
          <div className="md:col-span-1">
            <Logo variant="light" />
            <p className="text-[13.5px] text-[#F7EFE9]/70 mt-5 leading-relaxed">
              A sisterhood empowering women of the Diaspora through friendship, professional growth, and philanthropy.
            </p>
            <div className="flex items-center gap-3 mt-5">
              {[{ Icon: Instagram, label: 'Instagram' }, { Icon: Facebook, label: 'Facebook' }, { Icon: Linkedin, label: 'LinkedIn' }, { Icon: Youtube, label: 'YouTube' }].map(({ Icon, label }) => (
                <a key={label} href="#" aria-label={label}
                  className="w-9 h-9 rounded-full flex items-center justify-center border border-white/15 hover:border-[#CBA24B] hover:text-[#CBA24B] transition-colors">
                  <Icon size={16} />
                </a>
              ))}
            </div>
          </div>

          <div>
            <h4 className="eyebrow text-[#CBA24B] mb-4">Explore</h4>
            <ul className="space-y-2.5">
              {nav.map((n) => (
                <li key={n.to}>
                  <Link to={n.to} className="text-[13.5px] text-[#F7EFE9]/75 hover:text-[#F7EFE9] transition-colors">{n.label}</Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h4 className="eyebrow text-[#CBA24B] mb-4">Get Involved</h4>
            <ul className="space-y-2.5">
              <li><Link to="/donate" className="text-[13.5px] text-[#F7EFE9]/75 hover:text-[#F7EFE9]">Donate</Link></li>
              <li><Link to="/volunteer" className="text-[13.5px] text-[#F7EFE9]/75 hover:text-[#F7EFE9]">Volunteer & Join</Link></li>
              <li><Link to="/events" className="text-[13.5px] text-[#F7EFE9]/75 hover:text-[#F7EFE9]">Upcoming Events</Link></li>
              <li><Link to="/transparency" className="text-[13.5px] text-[#F7EFE9]/75 hover:text-[#F7EFE9]">Financial Transparency</Link></li>
            </ul>
          </div>

          <div>
            <h4 className="eyebrow text-[#CBA24B] mb-4">Contact</h4>
            <ul className="space-y-3 text-[13.5px] text-[#F7EFE9]/75">
              <li className="flex gap-2.5"><MapPin size={16} className="text-[#CBA24B] shrink-0 mt-0.5" /> {org.address}</li>
              <li className="flex gap-2.5"><Phone size={16} className="text-[#CBA24B] shrink-0 mt-0.5" /> {org.phone}</li>
              <li className="flex gap-2.5"><Mail size={16} className="text-[#CBA24B] shrink-0 mt-0.5" /> {org.email}</li>
            </ul>
          </div>
        </div>

        {/* Compliance bar */}
        <div className="mt-12 pt-7 border-t border-white/10">
          <div className="rounded-xl px-5 py-4 text-[12.5px] text-[#F7EFE9]/70 leading-relaxed" style={{ background: 'rgba(255,255,255,0.04)' }}>
            <strong className="text-[#F7EFE9]/90">{org.name}</strong> is a registered {org.status}.
            Mailing address: {org.address}.
            Contributions are tax-deductible to the extent permitted by law. <span className="italic">(Sample compliance details for demonstration.)</span>
          </div>
          <div className="flex flex-col md:flex-row items-center justify-between gap-4 mt-6">
            <p className="text-[12.5px] text-[#F7EFE9]/55">
              &copy; {new Date().getFullYear()} {org.name}. All rights reserved.
            </p>
            <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-2">
              {legal.map((l) => (
                <Link key={l.to} to={l.to} className="text-[12.5px] text-[#F7EFE9]/60 hover:text-[#CBA24B] transition-colors">{l.label}</Link>
              ))}
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}
