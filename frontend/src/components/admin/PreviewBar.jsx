import React from 'react';
import { Eye, X } from 'lucide-react';
import { PREVIEW_KEY } from '../../lib/api';
import { LEVELS, LEVEL_HELP } from './TeamList';

const set = (p) => { if (p) sessionStorage.setItem(PREVIEW_KEY, JSON.stringify(p)); else sessionStorage.removeItem(PREVIEW_KEY); window.location.reload(); };
const selCls = 'rounded-full border border-[#3B0A2E]/15 bg-white px-3 py-1.5 text-[12.5px] font-semibold text-[#3B0A2E] focus:outline-none focus:border-[#B4247E]';

export function PreviewBar({ preview }) {
  if (preview) {
    return (
      <div data-testid="admin-preview-banner" className="mb-6 rounded-2xl p-4 flex flex-wrap items-center gap-3 text-white" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
        <Eye size={18} />
        <p className="flex-1 min-w-[220px] text-[13.5px]">
          <b>Previewing as {LEVELS[preview.level]}</b> · {preview.mode === 'working' ? 'Fully working: changes are saved for real.' : 'Look only: nothing can be saved.'}
          <span className="block opacity-80 text-[12.5px]">{LEVEL_HELP[preview.level]}</span>
        </p>
        <select data-testid="admin-preview-mode" value={preview.mode} onChange={(e) => set({ ...preview, mode: e.target.value })} className={selCls} aria-label="Preview mode">
          <option value="look">Look only</option>
          <option value="working">Fully working</option>
        </select>
        <button data-testid="admin-preview-exit" onClick={() => set(null)} className="rounded-full bg-white text-[#3B0A2E] px-4 py-1.5 text-[12.5px] font-semibold flex items-center gap-1"><X size={14} /> Exit preview</button>
      </div>
    );
  }
  return (
    <div data-testid="admin-preview-start" className="mb-6 flex flex-wrap items-center gap-2 text-[13px] text-[#241019]/70">
      <Eye size={15} className="text-[#B4247E]" /> Preview Admin as
      {['content', 'members', 'money'].map((l) => (
        <button key={l} data-testid={`admin-preview-as-${l}`} onClick={() => set({ level: l, mode: 'look' })} className="rounded-full px-3 py-1 font-semibold border border-[#3B0A2E]/15 text-[#3B0A2E] hover:border-[#B4247E] hover:text-[#B4247E] transition-colors">{LEVELS[l]}</button>
      ))}
    </div>
  );
}
