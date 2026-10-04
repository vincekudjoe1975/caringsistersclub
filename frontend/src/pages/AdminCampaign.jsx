import React, { useEffect, useState } from 'react';
import { api } from '../lib/api';
import { useToast } from '../hooks/use-toast';
import { Loader2, Target, Save, Send, Heart, Mail } from 'lucide-react';

export default function AdminCampaign() {
  const { toast } = useToast();
  const [form, setForm] = useState({ campaign_title: '', campaign_subtitle: '', goal: '', deadline: '', thankyou_enabled: true, thankyou_threshold: '', thankyou_sender_name: '', thankyou_note: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [note, setNote] = useState('');
  const [sendingProgress, setSendingProgress] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);

  const sendTestReceipt = async () => {
    setSendingTest(true);
    try {
      const { data } = await api.post('/admin/email/test-receipt');
      if (data.sent) {
        toast({ title: 'Test receipt sent', description: `Check ${data.to} — a sample receipt is on its way.` });
      } else {
        toast({ title: 'Not delivered', description: data.detail || 'The provider could not deliver to your address.', variant: 'destructive' });
      }
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSendingTest(false);
    }
  };

  const sendProgress = async () => {
    if (!window.confirm('Send a progress update email to all past donors?')) return;
    setSendingProgress(true);
    try {
      const { data: r } = await api.post('/admin/campaign/send-progress', { message: note });
      toast({ title: 'Progress email sent', description: `We're ${r.percent}% there — ${r.sent} of ${r.recipients} donors emailed.` });
      setNote('');
    } catch (e) {
      toast({ title: 'Send failed', description: e?.response?.data?.detail || 'Please try again.', variant: 'destructive' });
    } finally {
      setSendingProgress(false);
    }
  };

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get('/admin/settings');
        setForm({
          campaign_title: data.campaign_title || '',
          campaign_subtitle: data.campaign_subtitle || '',
          goal: data.goal || '',
          deadline: data.deadline || '',
          thankyou_enabled: data.thankyou_enabled !== false,
          thankyou_threshold: data.thankyou_threshold ?? '',
          thankyou_sender_name: data.thankyou_sender_name || '',
          thankyou_note: data.thankyou_note || '',
        });
      } catch (e) {
        console.error('AdminCampaign: failed to load settings', e);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const save = async (e) => {
    e.preventDefault();
    const goalNum = Number(form.goal);
    if (!goalNum || goalNum <= 0) {
      toast({ title: 'Enter a valid goal amount', variant: 'destructive' });
      return;
    }
    setSaving(true);
    try {
      await api.put('/admin/settings', {
        campaign_title: form.campaign_title,
        campaign_subtitle: form.campaign_subtitle,
        goal: goalNum,
        deadline: form.deadline || '',
        thankyou_enabled: form.thankyou_enabled,
        thankyou_threshold: Number(form.thankyou_threshold) || 0,
        thankyou_sender_name: form.thankyou_sender_name,
        thankyou_note: form.thankyou_note,
      });
      toast({ title: 'Campaign updated', description: 'Your donor wall now reflects the changes.' });
    } catch (err) {
      toast({ title: 'Save failed', description: err?.response?.data?.detail || 'Try again', variant: 'destructive' });
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="flex items-center justify-center py-20"><Loader2 className="animate-spin text-[#B4247E]" size={32} /></div>;
  }

  return (
    <div className="max-w-xl">
      <form onSubmit={save} className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8">
        <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2">
          <Target size={20} className="text-[#B4247E]" /> Fundraising Campaign
        </h2>
        <p className="text-[#241019]/60 text-[13.5px] mb-6">These appear on the public donor wall and thermometer.</p>

        <div className="space-y-5">
          <div>
            <label className="text-[13px] font-semibold text-[#3B0A2E]">Eyebrow (small label)</label>
            <input value={form.campaign_subtitle} onChange={(e) => setForm({ ...form, campaign_subtitle: e.target.value })}
              placeholder="Our Community of Givers"
              className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
          </div>
          <div>
            <label className="text-[13px] font-semibold text-[#3B0A2E]">Campaign Title</label>
            <input value={form.campaign_title} onChange={(e) => setForm({ ...form, campaign_title: e.target.value })}
              placeholder="Together we're making it happen"
              className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
          </div>
          <div>
            <label className="text-[13px] font-semibold text-[#3B0A2E]">Fundraising Goal ($)</label>
            <div className="relative mt-1.5">
              <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3B0A2E] font-semibold">$</span>
              <input type="number" min={1} value={form.goal} onChange={(e) => setForm({ ...form, goal: e.target.value })}
                className="w-full rounded-lg border border-[#3B0A2E]/15 pl-8 pr-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
            </div>
          </div>
          <div>
            <label className="text-[13px] font-semibold text-[#3B0A2E]">Campaign Deadline <span className="text-[#241019]/40 font-normal">(optional)</span></label>
            <input type="date" value={form.deadline} onChange={(e) => setForm({ ...form, deadline: e.target.value })}
              className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
            <p className="text-[12px] text-[#241019]/50 mt-1.5">Shows a countdown on the donor wall. Leave empty for no deadline.</p>
          </div>
        </div>

        <div className="mt-8 pt-7 border-t border-[#3B0A2E]/10">
          <h3 className="font-serif text-[18px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2">
            <Heart size={18} className="text-[#B4247E]" /> Thank-You Automation
          </h3>
          <p className="text-[#241019]/60 text-[13px] mb-5">Automatically email a warm, personal note from a board member when a gift meets your large-gift threshold.</p>

          <label className="flex items-center gap-3 mb-5 cursor-pointer" data-testid="thankyou-enabled-toggle">
            <input type="checkbox" checked={form.thankyou_enabled}
              onChange={(e) => setForm({ ...form, thankyou_enabled: e.target.checked })}
              className="w-4 h-4 accent-[#B4247E]" />
            <span className="text-[13.5px] text-[#3B0A2E] font-medium">Send automatic thank-you emails for large gifts</span>
          </label>

          <div className={`space-y-5 ${form.thankyou_enabled ? '' : 'opacity-50 pointer-events-none'}`}>
            <div>
              <label className="text-[13px] font-semibold text-[#3B0A2E]">Large-Gift Threshold ($)</label>
              <div className="relative mt-1.5">
                <span className="absolute left-4 top-1/2 -translate-y-1/2 text-[#3B0A2E] font-semibold">$</span>
                <input type="number" min={0} value={form.thankyou_threshold} data-testid="thankyou-threshold-input"
                  onChange={(e) => setForm({ ...form, thankyou_threshold: e.target.value })}
                  className="w-full rounded-lg border border-[#3B0A2E]/15 pl-8 pr-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <p className="text-[12px] text-[#241019]/50 mt-1.5">Gifts at or above this amount trigger a personal thank-you.</p>
            </div>
            <div>
              <label className="text-[13px] font-semibold text-[#3B0A2E]">Sender (board member)</label>
              <input value={form.thankyou_sender_name} data-testid="thankyou-sender-input"
                onChange={(e) => setForm({ ...form, thankyou_sender_name: e.target.value })}
                placeholder="Fem Mansaray, Founder & President"
                className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
            </div>
            <div>
              <label className="text-[13px] font-semibold text-[#3B0A2E]">Personal Message</label>
              <textarea value={form.thankyou_note} rows={3} data-testid="thankyou-note-input"
                onChange={(e) => setForm({ ...form, thankyou_note: e.target.value })}
                className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E] resize-none" />
            </div>
          </div>
        </div>

        <button type="submit" disabled={saving} className="btn-magenta rounded-full px-7 py-3 font-semibold mt-7 flex items-center gap-2 disabled:opacity-60">
          {saving ? <><Loader2 className="animate-spin" size={16} /> Saving…</> : <><Save size={16} /> Save Campaign</>}
        </button>
      </form>

      <div className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8 mt-6">
        <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2">
          <Send size={20} className="text-[#B4247E]" /> Campaign Progress Email
        </h2>
        <p className="text-[#241019]/60 text-[13.5px] mb-5">Email all past donors a "we're X% there" update with the current progress bar. Add an optional personal note.</p>
        <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={3}
          placeholder="Optional note, e.g. 'Just two weeks left — help us cross the finish line!'"
          className="w-full rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E] resize-none mb-4" />
        <button onClick={sendProgress} disabled={sendingProgress}
          className="btn-magenta rounded-full px-7 py-3 font-semibold flex items-center gap-2 disabled:opacity-60">
          {sendingProgress ? <><Loader2 className="animate-spin" size={16} /> Sending…</> : <><Send size={16} /> Send Progress Update</>}
        </button>
      </div>

      <div className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8 mt-6">
        <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-1 flex items-center gap-2">
          <Mail size={20} className="text-[#B4247E]" /> Email Delivery Test
        </h2>
        <p className="text-[#241019]/60 text-[13.5px] mb-5">Send a sample branded donation receipt to your own admin inbox to confirm emails are being delivered.</p>
        <button onClick={sendTestReceipt} disabled={sendingTest} data-testid="send-test-receipt-btn"
          className="rounded-full px-7 py-3 font-semibold flex items-center gap-2 bg-white text-[#3B0A2E] disabled:opacity-60" style={{ border: '1px solid rgba(59,10,46,0.15)' }}>
          {sendingTest ? <><Loader2 className="animate-spin" size={16} /> Sending…</> : <><Mail size={16} /> Send Me a Test Receipt</>}
        </button>
      </div>
    </div>
  );
}
