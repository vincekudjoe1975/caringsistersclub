import React, { useState } from 'react';
import { Loader2, PenLine, CheckCircle2, UploadCloud, Send } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from './ui/dialog';
import { api, mediaSrc } from '../lib/api';
import { errMsg } from '../pages/Events';

const inp = 'w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]';

function StoryForm({ programSlug, onDone }) {
  const [form, setForm] = useState({ name: '', email: '', role: '', quote: '', photo_url: '' });
  const [busy, setBusy] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const upload = async (file) => {
    if (!file) return;
    const fd = new FormData();
    fd.append('file', file);
    setUploading(true); setError('');
    try { const { data } = await api.post('/stories/photo', fd, { headers: { 'Content-Type': 'multipart/form-data' } }); setForm((f) => ({ ...f, photo_url: data.url })); }
    catch (err) { setError(errMsg(err)); }
    finally { setUploading(false); }
  };
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true); setError('');
    try { await api.post('/stories', { ...form, program_slug: programSlug || '' }); onDone(); }
    catch (err) { setError(errMsg(err)); }
    finally { setBusy(false); }
  };
  return (
    <form onSubmit={submit} className="space-y-3 mt-1">
      <div className="grid grid-cols-2 gap-3">
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Name</label><input required value={form.name} onChange={set('name')} className={inp} data-testid="story-name-input" /></div>
        <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label><input required type="email" value={form.email} onChange={set('email')} className={inp} data-testid="story-email-input" /></div>
      </div>
      <div><label className="text-[13px] font-semibold text-[#3B0A2E]">How are you connected? (optional)</label><input value={form.role} onChange={set('role')} placeholder="Member since 2023" className={inp} data-testid="story-role-input" /></div>
      <div><label className="text-[13px] font-semibold text-[#3B0A2E]">Your story</label><textarea required rows={4} value={form.quote} onChange={set('quote')} className={`${inp} resize-y`} data-testid="story-quote-input" /></div>
      <div className="flex items-center gap-3">
        {form.photo_url && <img src={mediaSrc(form.photo_url)} alt="" className="w-12 h-12 rounded-full object-cover" />}
        <label className="text-[13px] font-semibold text-[#B4247E] flex items-center gap-2 cursor-pointer">
          {uploading ? <Loader2 size={15} className="animate-spin" /> : <UploadCloud size={15} />} {form.photo_url ? 'Change photo' : 'Add a photo (optional)'}
          <input type="file" accept="image/*" className="hidden" data-testid="story-photo-input" onChange={(e) => upload(e.target.files?.[0])} />
        </label>
      </div>
      {error && <p className="text-[13px] text-red-600" data-testid="story-error">{error}</p>}
      <p className="text-[11.5px] text-[#241019]/50">Our team reviews every story before it's shared. Your email is never published.</p>
      <button type="submit" disabled={busy || uploading} data-testid="story-submit-btn" className="btn-magenta rounded-full w-full py-3 font-semibold flex items-center justify-center gap-2 disabled:opacity-60">
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />} Share My Story
      </button>
    </form>
  );
}

export const ShareStory = ({ programSlug, className = '' }) => {
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState(false);
  return (
    <>
      <button onClick={() => { setDone(false); setOpen(true); }} data-testid="share-story-btn"
        className={`rounded-full px-6 py-3 font-semibold text-[14px] text-[#3B0A2E] hover:bg-[#faf2f7] inline-flex items-center gap-2 ${className}`} style={{ border: '1.5px solid #B4247E' }}>
        <PenLine size={16} /> Share Your Story
      </button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle className="font-serif text-[22px] text-[#3B0A2E]">Share your story</DialogTitle>
            <DialogDescription className="text-[13px] text-[#241019]/60">Tell us how the sisterhood has made a difference for you.</DialogDescription>
          </DialogHeader>
          {done ? (
            <div className="text-center py-4" data-testid="story-success">
              <CheckCircle2 size={44} className="text-[#B4247E] mx-auto mb-3" />
              <p className="font-serif text-[20px] text-[#3B0A2E] font-semibold mb-1">Thank you, sister!</p>
              <p className="text-[13.5px] text-[#241019]/65">Our team will review your story shortly. It may be featured on our website.</p>
            </div>
          ) : <StoryForm programSlug={programSlug} onDone={() => setDone(true)} />}
        </DialogContent>
      </Dialog>
    </>
  );
};
