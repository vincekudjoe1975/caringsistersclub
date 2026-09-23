import React from 'react';

export default function PageHero({ kicker, title, subtitle, align = 'left' }) {
  return (
    <section className="csc-hero-gradient pt-[132px] pb-16 md:pb-20 relative overflow-hidden">
      <div
        className="absolute -right-24 -top-24 w-96 h-96 rounded-full opacity-30"
        style={{ background: 'radial-gradient(circle, #D14FA0, transparent 70%)' }}
      />
      <div
        className="absolute -left-16 bottom-0 w-72 h-72 rounded-full opacity-20"
        style={{ background: 'radial-gradient(circle, #CBA24B, transparent 70%)' }}
      />
      <div className={`max-w-7xl mx-auto px-5 lg:px-8 relative ${align === 'center' ? 'text-center' : ''}`}>
        {kicker && <p className="eyebrow text-[#CBA24B] mb-4">{kicker}</p>}
        <h1 className="font-serif text-[#F7EFE9] text-[40px] md:text-[56px] leading-[1.05] font-semibold max-w-3xl" style={align === 'center' ? { marginInline: 'auto' } : {}}>
          {title}
        </h1>
        {subtitle && (
          <p className={`text-[#F7EFE9]/75 text-[16px] md:text-[18px] mt-5 max-w-2xl leading-relaxed ${align === 'center' ? 'mx-auto' : ''}`}>
            {subtitle}
          </p>
        )}
      </div>
    </section>
  );
}
