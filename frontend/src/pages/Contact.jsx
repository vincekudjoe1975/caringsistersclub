import React, { useState } from 'react';
import { org, faqs } from '../mock/mock';
import { api } from '../lib/api';
import PageHero from '../components/PageHero';
import Reveal from '../components/Reveal';
import { MapPin, Phone, Mail, Clock, Send, Loader2 } from 'lucide-react';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../components/ui/accordion';
import { useToast } from '../hooks/use-toast';

export default function Contact() {
  const [form, setForm] = useState({ name: '', email: '', subject: '', message: '' });
  const [sending, setSending] = useState(false);
  const { toast } = useToast();

  const submit = async (e) => {
    e.preventDefault();
    setSending(true);
    try {
      await api.post('/submissions', { type: 'contact', ...form });
      toast({ title: 'Message sent!', description: `Thank you, ${form.name}. We'll respond to ${form.email} shortly.` });
      setForm({ name: '', email: '', subject: '', message: '' });
    } catch (err) {
      toast({ title: 'Message not sent', description: err?.response?.status === 429 ? 'You\'ve sent a few requests in a row. Please wait a minute and try again.' : (err?.response?.data?.detail || 'Something went wrong. Please check your connection and try again.'), variant: 'destructive' });
    } finally {
      setSending(false);
    }
  };

  const info = [
    { icon: MapPin, label: 'Address', value: org.address },
    { icon: Phone, label: 'Phone', value: org.phone },
    { icon: Mail, label: 'Email', value: org.email },
    { icon: Clock, label: 'Hours', value: org.hours },
  ];

  return (
    <div>
      <PageHero
        kicker="Get in Touch"
        title="We'd love to hear from you"
        subtitle="Questions about membership, events, partnerships, or giving? Reach out and a member of our team will respond."
      />

      <section className="py-16 lg:py-24">
        <div className="max-w-6xl mx-auto px-5 lg:px-8 grid lg:grid-cols-[1fr_1.2fr] gap-12">
          <Reveal className="space-y-5">
            {info.map((c) => {
              const Icon = c.icon;
              return (
                <div key={c.label} className="flex gap-4 bg-white rounded-2xl p-6 border border-[#3B0A2E]/8 card-hover">
                  <span className="w-12 h-12 rounded-xl flex items-center justify-center shrink-0" style={{ background: 'linear-gradient(135deg,#3B0A2E,#B4247E)' }}>
                    <Icon size={22} className="text-white" />
                  </span>
                  <div>
                    <p className="eyebrow text-[#B4247E] mb-1">{c.label}</p>
                    <p className="text-[#3B0A2E] text-[15px]">{c.value}</p>
                  </div>
                </div>
              );
            })}
            <p className="text-[12px] text-[#241019]/50 italic">Contact details are sample placeholders for demonstration.</p>
          </Reveal>

          <Reveal delay={120}>
            <form onSubmit={submit} className="bg-white rounded-2xl p-8 border border-[#3B0A2E]/8 space-y-5">
              <div className="grid sm:grid-cols-2 gap-5">
                <div>
                  <label className="text-[13px] font-semibold text-[#3B0A2E]">Name</label>
                  <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} data-testid="contact-name-input"
                    className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
                </div>
                <div>
                  <label className="text-[13px] font-semibold text-[#3B0A2E]">Email</label>
                  <input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} data-testid="contact-email-input"
                    className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
                </div>
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Subject</label>
                <input required value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })} data-testid="contact-subject-input"
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-2.5 text-[14px] focus:outline-none focus:border-[#B4247E]" />
              </div>
              <div>
                <label className="text-[13px] font-semibold text-[#3B0A2E]">Message</label>
                <textarea required rows={5} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} data-testid="contact-message-input"
                  className="w-full mt-1.5 rounded-lg border border-[#3B0A2E]/15 px-4 py-3 text-[14px] focus:outline-none focus:border-[#B4247E] resize-none" />
              </div>
              <button type="submit" disabled={sending} data-testid="contact-submit-btn" className="btn-magenta rounded-full px-8 py-3.5 font-semibold flex items-center gap-2 disabled:opacity-60">
                {sending ? <><Loader2 size={16} className="animate-spin" /> Sending…</> : <>Send Message <Send size={16} /></>}
              </button>
            </form>
          </Reveal>
        </div>
      </section>

      {/* FAQ */}
      <section className="py-16 lg:py-24" style={{ background: '#F7EFE9' }}>
        <div className="max-w-3xl mx-auto px-5 lg:px-8">
          <div className="text-center mb-12">
            <p className="eyebrow text-[#B4247E] mb-4">Frequently Asked</p>
            <h2 className="font-serif text-[30px] lg:text-[40px] text-[#3B0A2E] font-semibold">Questions & answers</h2>
          </div>
          <Accordion type="single" collapsible className="space-y-4">
            {faqs.map((f, i) => (
              <AccordionItem key={f.q} value={`item-${i}`} className="bg-white rounded-xl border border-[#3B0A2E]/8 px-6">
                <AccordionTrigger className="text-left font-serif text-[17px] text-[#3B0A2E] hover:no-underline">{f.q}</AccordionTrigger>
                <AccordionContent className="text-[#241019]/70 text-[14.5px] leading-relaxed">{f.a}</AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
        </div>
      </section>
    </div>
  );
}
