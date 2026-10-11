import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { api } from '../../lib/api';
import { Avatar } from './Avatar';

export default function SisterMap() {
  const [d, setD] = useState(null);
  useEffect(() => { api.get('/members/map').then(({ data }) => setD(data)).catch(() => setD({ cities: [], on_map: false })); }, []);
  if (!d) return <p className="text-[#241019]/50 py-10 text-center">Loading map…</p>;
  const center = d.cities.length ? [d.cities.reduce((a, c) => a + c.lat, 0) / d.cities.length, d.cities.reduce((a, c) => a + c.lon, 0) / d.cities.length] : [39.74, -75.55];
  return (
    <div data-testid="sister-map">
      {!d.on_map && <p data-testid="sister-map-optin-hint" className="text-[13.5px] text-[#241019]/70 mb-3 bg-white rounded-xl px-4 py-3 border border-[#3B0A2E]/8">You're not on the map yet. Turn on "Show my city on the sister map" in My Profile to appear (only your city is shown).</p>}
      <div className="rounded-2xl overflow-hidden border border-[#3B0A2E]/10 h-[420px] sm:h-[520px] relative z-0">
        <MapContainer center={center} zoom={d.cities.length ? 9 : 8} scrollWheelZoom={false} className="h-full w-full">
          <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
          {d.cities.map((c) => (
            <CircleMarker key={c.city} center={[c.lat, c.lon]} radius={10 + Math.min(c.count, 10) * 2} pathOptions={{ color: '#3B0A2E', weight: 2, fillColor: '#B4247E', fillOpacity: 0.75 }}>
              <Popup>
                <div data-testid={`map-city-${c.city}`} className="min-w-[180px]">
                  <p className="font-semibold text-[#3B0A2E] text-[14px]">{c.city} · {c.count} sister{c.count === 1 ? '' : 's'}</p>
                  <ul className="mt-2 space-y-1.5 max-h-48 overflow-y-auto">{c.sisters.map((s) => (
                    <li key={s.user_id} className="flex items-center gap-2 text-[13px]"><Avatar name={s.name} src={s.picture} size={26} /> <span>{s.name}</span>{s.office && <span className="text-[#B4247E] text-[11.5px] font-semibold">{s.office}</span>}</li>
                  ))}</ul>
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
      <p data-testid="sister-map-count" className="text-[12.5px] text-[#241019]/55 mt-2">{d.cities.reduce((a, c) => a + c.count, 0)} sisters in {d.cities.length} cit{d.cities.length === 1 ? 'y' : 'ies'}{d.unmapped ? ` · ${d.unmapped} more cit${d.unmapped === 1 ? 'y' : 'ies'} still locating, check back shortly` : ''}. Tap a circle to see who lives there.</p>
    </div>
  );
}
