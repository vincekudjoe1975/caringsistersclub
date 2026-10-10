import { useEffect, useState } from 'react';
import { api, mediaSrc } from './api';
import { mission as mockMission, pillars as mockPillars, testimonials as mockTestimonials } from '../mock/mock';

const FALLBACK = {
  mission_heading: mockMission.heading, mission_title: 'Bridging the distance for women in the Diaspora',
  mission_body: mockMission.body, mission_quote: mockMission.quote, mission_image: '',
  pillars: mockPillars, testimonials: mockTestimonials.map((t, i) => ({ ...t, id: `m${i}`, photo_url: '' })),
};
let cache = null;

export const imgSrc = (url, fallback = '') => (!url ? fallback : url.startsWith('/api/') ? mediaSrc(url) : url);
export const DEFAULT_MISSION_IMAGE = mockMission.image;

export function useHomeContent() {
  const [data, setData] = useState(cache || FALLBACK);
  useEffect(() => {
    if (cache) return;
    api.get('/home-content').then(({ data: d }) => { cache = d; setData(d); })
      .catch((e) => console.error('Home content: load failed', e));
  }, []);
  return data;
}

export const resetHomeContentCache = () => { cache = null; };

export async function uploadImage(file, category, title) {
  const fd = new FormData();
  fd.append('file', file); fd.append('category', category); fd.append('title', title || file.name);
  const { data } = await api.post('/media', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
  return data.url;
}
