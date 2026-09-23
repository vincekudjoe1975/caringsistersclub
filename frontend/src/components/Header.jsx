import React, { useState, useEffect } from 'react';
import { NavLink, Link, useLocation } from 'react-router-dom';
import { nav } from '../mock/mock';
import Logo from './Logo';
import { Menu, X, Heart, LogIn } from 'lucide-react';
import { Sheet, SheetContent, SheetTrigger } from './ui/sheet';

export default function Header() {
  const [scrolled, setScrolled] = useState(false);
  const [open, setOpen] = useState(false);
  const location = useLocation();

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 24);
    onScroll();
    window.addEventListener('scroll', onScroll);
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  useEffect(() => { setOpen(false); }, [location.pathname]);

  return (
    <header
      className="fixed top-0 left-0 right-0 z-50 transition-all duration-300"
      style={{
        background: scrolled ? 'rgba(41,6,31,0.96)' : 'rgba(41,6,31,0.55)',
        backdropFilter: 'blur(12px)',
        borderBottom: scrolled ? '1px solid rgba(203,162,75,0.25)' : '1px solid transparent',
        boxShadow: scrolled ? '0 10px 30px -18px rgba(0,0,0,0.6)' : 'none',
      }}
    >
      <div className="max-w-7xl mx-auto px-5 lg:px-8 flex items-center justify-between h-[76px]">
        <Logo variant="light" compact={scrolled} />

        <nav className="hidden lg:flex items-center gap-7">
          {nav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `text-[14px] tracking-wide link-underline transition-colors ${
                  isActive ? 'text-[#CBA24B]' : 'text-[#F7EFE9]/85 hover:text-[#F7EFE9]'
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden lg:flex items-center gap-3">
          <Link
            to="/volunteer"
            className="text-[13px] text-[#F7EFE9]/85 hover:text-[#F7EFE9] flex items-center gap-1.5 transition-colors"
          >
            <LogIn size={15} /> Member Login
          </Link>
          <Link
            to="/donate"
            className="btn-magenta rounded-full px-6 py-2.5 text-[14px] font-semibold flex items-center gap-2"
          >
            <Heart size={15} className="fill-white" /> Donate
          </Link>
        </div>

        <div className="lg:hidden flex items-center gap-3">
          <Link to="/donate" className="btn-magenta rounded-full px-4 py-2 text-[13px] font-semibold flex items-center gap-1.5">
            <Heart size={13} className="fill-white" /> Donate
          </Link>
          <Sheet open={open} onOpenChange={setOpen}>
            <SheetTrigger asChild>
              <button aria-label="Open menu" className="text-[#F7EFE9] p-1">
                <Menu size={26} />
              </button>
            </SheetTrigger>
            <SheetContent side="right" className="w-[300px] border-0 p-0" style={{ background: '#29061F' }}>
              <div className="p-6 flex items-center justify-between">
                <Logo variant="light" compact />
                <button onClick={() => setOpen(false)} className="text-[#F7EFE9]"><X size={24} /></button>
              </div>
              <div className="flex flex-col px-6 mt-4">
                {nav.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      `py-3 text-[16px] border-b border-white/10 ${isActive ? 'text-[#CBA24B]' : 'text-[#F7EFE9]/90'}`
                    }
                  >
                    {item.label}
                  </NavLink>
                ))}
                <Link to="/volunteer" className="py-3 text-[16px] border-b border-white/10 text-[#F7EFE9]/90 flex items-center gap-2">
                  <LogIn size={16} /> Member Login
                </Link>
                <Link to="/donate" className="btn-magenta rounded-full px-6 py-3 text-center font-semibold mt-6">
                  Donate Now
                </Link>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  );
}
