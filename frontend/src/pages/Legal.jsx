import React from 'react';
import { org } from '../mock/mock';
import PageHero from '../components/PageHero';

const content = {
  privacy: {
    kicker: 'Legal',
    title: 'Privacy Policy',
    sections: [
      { h: 'Overview', p: `${org.name} (“we,” “us”) respects your privacy. This policy explains what information we collect, how we use it, and the choices you have. This is a sample policy provided for demonstration.` },
      { h: 'Information We Collect', p: 'We collect information you provide directly—such as your name, email, phone number, and messages—when you contact us, donate, volunteer, or register for events. We also collect limited analytics data to improve our website.' },
      { h: 'How We Use Information', p: 'We use your information to respond to inquiries, process donations, coordinate volunteering and events, send updates you opt into, and comply with legal obligations. We never sell your personal information.' },
      { h: 'Cookies & Analytics', p: 'Our website may use cookies and privacy-respecting analytics to understand usage. You can control cookies through your browser settings.' },
      { h: 'Data Security', p: 'We implement reasonable administrative, technical, and physical safeguards to protect your information. No method of transmission is 100% secure.' },
      { h: 'Your Rights', p: 'You may request access to, correction of, or deletion of your personal information by contacting us at ' + org.email + '.' },
    ],
  },
  terms: {
    kicker: 'Legal',
    title: 'Terms of Service',
    sections: [
      { h: 'Acceptance of Terms', p: `By accessing ${org.shortName}’s website, you agree to these Terms of Service. This is a sample document for demonstration.` },
      { h: 'Use of the Site', p: 'You agree to use the site lawfully and not to disrupt, damage, or gain unauthorized access to any part of the website or its systems.' },
      { h: 'Donations', p: 'Donations made through this site are voluntary and, where indicated, tax-deductible. In this demo, no real payments are processed.' },
      { h: 'Intellectual Property', p: 'All content, logos, and materials on this site are the property of the organization unless otherwise noted, and may not be reused without permission.' },
      { h: 'Limitation of Liability', p: 'The site is provided “as is.” We are not liable for damages arising from the use of, or inability to use, the site.' },
      { h: 'Changes', p: 'We may update these terms from time to time. Continued use of the site constitutes acceptance of the updated terms.' },
    ],
  },
  accessibility: {
    kicker: 'Legal',
    title: 'Accessibility Statement (ADA)',
    sections: [
      { h: 'Our Commitment', p: `${org.name} is committed to ensuring digital accessibility for people with disabilities and to conforming with the Web Content Accessibility Guidelines (WCAG) 2.1 Level AA.` },
      { h: 'Measures We Take', p: 'We use semantic HTML, descriptive image alt text, sufficient color contrast, keyboard-navigable menus, and clearly labeled forms to support assistive technologies.' },
      { h: 'Ongoing Effort', p: 'Accessibility is an ongoing effort. We regularly review our website and welcome feedback that helps us improve the experience for all users.' },
      { h: 'Feedback', p: 'If you encounter any accessibility barrier, please contact us at ' + org.email + ' or ' + org.phone + ' so we can assist you and address the issue promptly.' },
    ],
  },
  donor: {
    kicker: 'Legal',
    title: 'Donor Privacy Policy',
    sections: [
      { h: 'Respect for Donors', p: `${org.name} values the trust of our donors and is committed to protecting their privacy, in alignment with Charity Navigator best practices.` },
      { h: 'Information Collected', p: 'When you donate, we collect your name, contact details, and gift information. Payment details are handled securely by our payment processor and are not stored on our servers.' },
      { h: 'No Sharing or Selling', p: 'We do not sell, trade, or share our donors’ personal information with any third party for their marketing purposes.' },
      { h: 'Donor Choices', p: 'Donors may request to remain anonymous, opt out of communications, or have their information removed from our lists at any time by contacting ' + org.email + '.' },
      { h: 'Receipts', p: 'All donors receive a written acknowledgment for tax purposes. Contributions are tax-deductible to the extent allowed by law.' },
    ],
  },
};

export default function Legal({ type }) {
  const data = content[type] || content.privacy;
  return (
    <div>
      <PageHero kicker={data.kicker} title={data.title} />
      <section className="py-16 lg:py-24">
        <div className="max-w-3xl mx-auto px-5 lg:px-8">
          <p className="text-[13px] text-[#241019]/50 italic mb-10">Last updated: {new Date().toLocaleDateString('en-US', { month: 'long', year: 'numeric' })}. This is a sample legal document provided for demonstration and should be reviewed by counsel before publishing.</p>
          <div className="space-y-9">
            {data.sections.map((s) => (
              <div key={s.h}>
                <h2 className="font-serif text-[22px] text-[#3B0A2E] font-semibold mb-3">{s.h}</h2>
                <p className="text-[#241019]/75 text-[15.5px] leading-relaxed">{s.p}</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
