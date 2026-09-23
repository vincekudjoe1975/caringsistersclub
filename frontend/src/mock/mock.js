// MOCK DATA for Caring Sisters Club clone + grant-compliance build.
// NOTE: All organizational/legal/financial details below are SAMPLE/DEMO
// placeholders and are NOT real. Replace with verified data before launch.

import femImg from '../assets/team/fem.jpg';
import yeamaImg from '../assets/team/yeama.jpg';
import patriciaImg from '../assets/team/patricia.jpg';
import josephineImg from '../assets/team/josephine.jpg';
import finnahImg from '../assets/team/finnah.jpg';
import tiggyImg from '../assets/team/tiggy.jpg';

export const org = {
  name: 'The Caring Sisters Club, Inc.',
  shortName: 'Caring Sisters Club',
  tagline: 'Where care, community, and compassion meet.',
  ein: '88-1234567', // DEMO placeholder EIN
  status: '501(c)(3) Tax-Exempt Nonprofit Organization',
  founded: 2019,
  address: '1450 Community Way, Suite 210, Atlanta, GA 30303', // DEMO
  phone: '(404) 555-0182', // DEMO
  email: 'hello@caringsistersclub.org',
  hours: 'Mon–Fri, 9:00 AM – 5:00 PM ET',
  social: { instagram: '#', facebook: '#', linkedin: '#', youtube: '#' },
  logoText: { top: 'CARING SISTERS', sub: 'club', motto: 'Love · Respect · Empowerment' },
};

export const nav = [
  { label: 'Home', to: '/' },
  { label: 'About', to: '/about' },
  { label: 'Leadership', to: '/leadership' },
  { label: 'Initiatives', to: '/initiatives' },
  { label: 'Events', to: '/events' },
  { label: 'Gallery', to: '/gallery' },
  { label: 'Transparency', to: '/transparency' },
  { label: 'Contact', to: '/contact' },
];

export const hero = {
  kicker: 'Welcome to Caring Sisters Club',
  title: 'Connecting & Empowering Women of the Diaspora',
  subtitle:
    'A powerful professional network fostering friendship, mutual respect, and philanthropic growth globally.',
  image:
    'https://images.unsplash.com/photo-1709810529099-0ce6102692df?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzR8MHwxfHNlYXJjaHwzfHxwcm9mZXNzaW9uYWwlMjBCbGFjayUyMHdvbWVufGVufDB8fHx8MTc5MDE4NDcwOHww&ixlib=rb-4.1.0&q=85',
};

export const mission = {
  heading: 'Our Mission',
  body:
    'Caring Sisters Club, Inc. is dedicated to bridging the distance for women in the Diaspora. We provide a powerhouse platform for professional business elevation, comprehensive housing assistance, and collaborative philanthropic endeavors. By fostering a community rooted in friendship and mutual respect, we transform individual ambition into shared empowerment, ensuring every sister thrives in her journey toward success.',
  quote: 'Through shared strength, we transform collective vision into lasting community change.',
  image:
    'https://images.unsplash.com/photo-1508002366005-75a695ee2d17?crop=entropy&cs=srgb&fm=jpg&ixid=M3w4NjA1NzR8MHwxfHNlYXJjaHw0fHxwcm9mZXNzaW9uYWwlMjBCbGFjayUyMHdvbWVufGVufDB8fHx8MTc5MDE4NDcwOHww&ixlib=rb-4.1.0&q=85',
};

export const pillars = [
  {
    icon: 'Briefcase',
    title: 'Professional Empowerment',
    text: 'Connect with high-achieving women from the Diaspora to scale your business, share professional insights, and foster mutual growth in a supportive hub designed for excellence.',
    to: '/initiatives',
    cta: 'Explore Opportunities',
  },
  {
    icon: 'HeartHandshake',
    title: 'Philanthropy',
    text: 'Join our collective mission to solve the evolving challenges women face and spearhead philanthropic endeavors that empower communities while building lifelong bonds of friendship.',
    to: '/donate',
    cta: 'Join the Cause',
  },
  {
    icon: 'Home',
    title: 'Housing Assistance',
    text: 'We provide comprehensive housing navigation, emergency support, and resource connection so every sister has a stable foundation to build her future upon.',
    to: '/initiatives',
    cta: 'Learn More',
  },
];

export const stats = [
  { value: '2,400+', label: 'Sisters in our network' },
  { value: '38', label: 'Community programs delivered' },
  { value: '$610K', label: 'Granted to member initiatives' },
  { value: '14', label: 'Cities across the Diaspora' },
];

export const values = [
  { icon: 'Heart', title: 'Love', text: 'We lead with empathy, meeting every sister where she is with genuine care.' },
  { icon: 'Shield', title: 'Respect', text: 'Mutual respect is the foundation of trust that holds our sisterhood together.' },
  { icon: 'Sparkles', title: 'Empowerment', text: 'We equip women with tools, mentorship, and capital to rise and lead.' },
  { icon: 'Users', title: 'Community', text: 'We invest in the collective, knowing our impact multiplies when we grow together.' },
];

export const story = [
  { year: '2019', title: 'A Circle of Ten', text: 'Ten women of the Diaspora gathered around a kitchen table with a shared belief: no sister should build alone.' },
  { year: '2021', title: 'Formal 501(c)(3) Status', text: 'The club incorporated as a nonprofit, launching its first mentorship and housing-support cohort.' },
  { year: '2023', title: 'Regional Expansion', text: 'Chapters opened across 14 cities, delivering workshops, grants, and community drives.' },
  { year: '2025', title: 'The Sisterhood Fund', text: 'We launched a member grant fund distributing over $600K toward member-led businesses and relief.' },
];

export const board = [
  { name: 'Fem Mansaray', role: 'Founder & President', photo: femImg, bio: 'Founder and President of Caring Sisters Club, leading the vision to connect and empower women of the Diaspora.' },
  { name: 'Yeama Conteh', role: 'Co-Founder & Vice-President', photo: yeamaImg, bio: 'Co-Founder and Vice-President, championing member support, education, and community programs.' },
  { name: 'Patricia Nguessan', role: 'Co-Founder & Board Member', photo: patriciaImg, bio: 'Co-Founder and Board Member dedicated to sisterhood, service, and philanthropic impact.' },
  { name: 'Josephine Margai', role: 'Co-Founder & Board Member', photo: josephineImg, bio: 'Co-Founder and Board Member helping steward the club\u2019s mission and community engagement.' },
  { name: 'Finnah Mansaray', role: 'Co-Founder & Board Member', photo: finnahImg, bio: 'Co-Founder and Board Member supporting governance and the growth of the sisterhood.' },
  { name: 'Tiggy Steves', role: 'Media & Organizing Secretary', photo: tiggyImg, bio: 'Media and Organizing Secretary, coordinating communications, events, and outreach.' },
];

export const executives = [];

export const governance = [
  { title: 'Conflict of Interest Policy', desc: 'All directors annually disclose potential conflicts to protect the organization’s integrity.' },
  { title: 'Whistleblower Policy', desc: 'Confidential channels allow staff and volunteers to report concerns without retaliation.' },
  { title: 'Document Retention Policy', desc: 'Records are retained and disposed of per IRS and state nonprofit requirements.' },
  { title: 'Board Governance Charter', desc: 'Defines board roles, term limits, quorum, and fiduciary responsibilities.' },
];

export const financials = {
  form990: [
    { year: '2024', size: '1.2 MB', href: '#' },
    { year: '2023', size: '1.1 MB', href: '#' },
    { year: '2022', size: '0.9 MB', href: '#' },
  ],
  annualReports: [
    { year: '2024', size: '4.6 MB', href: '#' },
    { year: '2023', size: '4.1 MB', href: '#' },
  ],
  breakdown: [
    { label: 'Programs & Services', pct: 82, color: 'var(--csc-magenta)' },
    { label: 'Administration', pct: 11, color: 'var(--csc-plum-soft)' },
    { label: 'Fundraising', pct: 7, color: 'var(--csc-gold)' },
  ],
};

export const initiatives = [
  { title: 'Business Elevation Lab', category: 'Professional', image: 'https://images.pexels.com/photos/8555600/pexels-photo-8555600.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', text: 'A 12-week accelerator pairing members with mentors, capital readiness coaching, and a pitch showcase.' },
  { title: 'Sisterhood Housing Support', category: 'Housing', image: 'https://images.unsplash.com/photo-1628717341663-0007b0ee2597?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', text: 'Emergency housing navigation, rental assistance, and relocation resources for sisters in transition.' },
  { title: 'Community Care Drives', category: 'Philanthropy', image: 'https://images.unsplash.com/photo-1593113616828-6f22bca04804?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', text: 'Quarterly food, wellness, and back-to-school drives serving families across our chapter cities.' },
  { title: 'Leadership & Mentorship', category: 'Professional', image: 'https://images.unsplash.com/photo-1590650046871-92c887180603?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', text: 'Structured mentorship circles connecting emerging leaders with seasoned executives.' },
  { title: 'Wellness Workshops', category: 'Community', image: 'https://images.unsplash.com/photo-1652148439208-3e73641d0725?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', text: 'Mental health, financial literacy, and self-care workshops led by member experts.' },
  { title: 'The Sisterhood Fund', category: 'Philanthropy', image: 'https://images.pexels.com/photos/6647027/pexels-photo-6647027.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', text: 'Micro-grants distributed to member-led businesses and community relief projects.' },
];

export const events = [
  { id: 1, date: '2025-08-16', time: '10:00 AM', title: 'Annual Sisterhood Summit', location: 'Atlanta Convention Center, GA', category: 'Summit', spots: 120, image: 'https://images.pexels.com/photos/7648057/pexels-photo-7648057.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', desc: 'A full-day gathering of keynotes, breakout labs, and a philanthropy gala celebrating our impact.' },
  { id: 2, date: '2025-09-06', time: '1:00 PM', title: 'Business Elevation Lab — Fall Cohort', location: 'Virtual (Zoom)', category: 'Workshop', spots: 40, image: 'https://images.unsplash.com/photo-1590650046871-92c887180603?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', desc: 'Kickoff session for our 12-week accelerator. Open to new and returning members.' },
  { id: 3, date: '2025-09-20', time: '9:00 AM', title: 'Community Care Drive', location: 'Houston Community Hub, TX', category: 'Service', spots: 60, image: 'https://images.unsplash.com/photo-1593113616828-6f22bca04804?crop=entropy&cs=srgb&fm=jpg&q=85&w=940', desc: 'Volunteer to pack and distribute wellness and back-to-school kits to local families.' },
  { id: 4, date: '2025-10-11', time: '6:00 PM', title: 'Leadership Circle Mixer', location: 'Brooklyn, NY', category: 'Networking', spots: 80, image: 'https://images.pexels.com/photos/8555600/pexels-photo-8555600.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', desc: 'An evening of intentional networking connecting emerging and established sisters.' },
];

export const gallery = [
  { src: 'https://images.unsplash.com/photo-1607748851687-ba9a10438621?crop=entropy&cs=srgb&fm=jpg&q=85&w=900', caption: 'Chapter leaders at the 2024 Summit', tall: true },
  { src: 'https://images.unsplash.com/photo-1707409066859-a90674383d19?crop=entropy&cs=srgb&fm=jpg&q=85&w=900', caption: 'Celebrating our mentorship graduates' },
  { src: 'https://images.pexels.com/photos/8995950/pexels-photo-8995950.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', caption: 'Sisters supporting sisters' },
  { src: 'https://images.unsplash.com/photo-1628717341663-0007b0ee2597?crop=entropy&cs=srgb&fm=jpg&q=85&w=900', caption: 'Community Care Drive volunteers', tall: true },
  { src: 'https://images.unsplash.com/photo-1607748862156-7c548e7e98f4?crop=entropy&cs=srgb&fm=jpg&q=85&w=900', caption: 'Joyful moments at the Leadership Mixer' },
  { src: 'https://images.pexels.com/photos/7648057/pexels-photo-7648057.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', caption: 'Registration at the Sisterhood Summit' },
  { src: 'https://images.unsplash.com/photo-1636987050384-9b079c700f63?crop=entropy&cs=srgb&fm=jpg&q=85&w=900', caption: 'United in purpose', tall: true },
  { src: 'https://images.pexels.com/photos/6647027/pexels-photo-6647027.jpeg?auto=compress&cs=tinysrgb&dpr=2&h=650&w=940', caption: 'Distributing care packages' },
];

export const donationTiers = [
  { amount: 25, label: 'Friend', desc: 'Provides a wellness kit for a sister in need.' },
  { amount: 50, label: 'Advocate', desc: 'Sponsors a workshop seat for an emerging leader.' },
  { amount: 100, label: 'Champion', desc: 'Funds one week of housing navigation support.' },
  { amount: 250, label: 'Patron', desc: 'Backs a member business through the Elevation Lab.' },
];

export const testimonials = [
  { quote: 'The Caring Sisters Club gave me a mentor, a grant, and a sisterhood. My business tripled in a year.', name: 'Adaeze N.', role: 'Elevation Lab Graduate' },
  { quote: 'When I needed housing support, my sisters showed up. This community is family.', name: 'Louise M.', role: 'Member since 2022' },
  { quote: 'I found my leadership voice here. Now I mentor five other women.', name: 'Chantal B.', role: 'Chapter Lead, Brooklyn' },
];

export const faqs = [
  { q: 'How do I become a member?', a: 'Complete the membership form on our Volunteer & Join page. A chapter lead will reach out within 3 business days.' },
  { q: 'Are my donations tax-deductible?', a: 'Yes. Caring Sisters Club, Inc. is a 501(c)(3) organization (EIN 88-1234567, demo). Donations are tax-deductible to the extent allowed by law.' },
  { q: 'How are funds used?', a: '82 cents of every dollar goes directly to programs. See our Transparency page for Form 990 filings and annual reports.' },
  { q: 'Can I volunteer without becoming a member?', a: 'Absolutely. Volunteers are welcome at all community events—just fill out the volunteer form.' },
];
