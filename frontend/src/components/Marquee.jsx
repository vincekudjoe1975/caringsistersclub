import React from 'react';

export default function Marquee({ items = [], bg = '#B4247E', color = '#F7EFE9' }) {
  const doubled = [...items, ...items];
  return (
    <div className="overflow-hidden py-4" style={{ background: bg }} aria-hidden="true">
      <div className="csc-marquee-track">
        {doubled.map((word, i) => (
          <span key={`${word}-${i}`} className="inline-flex items-center">
            <span className="font-serif italic text-[22px] md:text-[26px] px-6" style={{ color }}>{word}</span>
            <span className="text-[#CBA24B] text-[18px]">&#10022;</span>
          </span>
        ))}
      </div>
    </div>
  );
}
