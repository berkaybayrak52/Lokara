'use client';

import 'leaflet/dist/leaflet.css';

import L from 'leaflet';
import markerIcon2x from 'leaflet/dist/images/marker-icon-2x.png';
import markerIcon from 'leaflet/dist/images/marker-icon.png';
import markerShadow from 'leaflet/dist/images/marker-shadow.png';
import { useEffect, useRef } from 'react';

import type { BuildingSummary } from '@/lib/contracts';
import { BUILDING_TYPE_LABELS } from '@/lib/contracts';

// Marker-Icon-Fix: unter Bundlern zeigen Leaflets Standard-Pfade sonst 404.
const DEFAULT_ICON = L.icon({
  iconUrl: markerIcon.src,
  iconRetinaUrl: markerIcon2x.src,
  shadowUrl: markerShadow.src,
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

function escapeHtml(value: string): string {
  return value.replace(
    /[&<>"']/g,
    (char) =>
      ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char] ?? char,
  );
}

/**
 * Karten-Ansicht der Objekte (O9): Leaflet imperativ (React 19-sicher), OSM-
 * Kacheln, ein Pin je Objekt mit Koordinaten. Popup: Name (Link) · Adresse ·
 * Gebäudeart im Klartext. Ohne Koordinaten → ruhiger Hinweis statt leerer Fläche.
 */
export function BuildingMap({
  accountId,
  buildings,
}: {
  accountId: string;
  buildings: BuildingSummary[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const map = L.map(container).setView([51.2, 10.4], 6);
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap-Mitwirkende',
      maxZoom: 19,
    }).addTo(map);

    const markers: L.Marker[] = [];
    for (const building of buildings) {
      if (building.latitude === null || building.longitude === null) continue;
      const marker = L.marker([building.latitude, building.longitude], { icon: DEFAULT_ICON }).addTo(
        map,
      );
      const typeLabel = BUILDING_TYPE_LABELS[building.buildingType] ?? building.buildingType;
      const href = `/a/${accountId}/objekte/${building.id}`;
      marker.bindPopup(
        `<a href="${href}" style="font-weight:600;color:#1a6558">${escapeHtml(building.name)}</a>` +
          `<br><span style="color:#5c6a6b">${escapeHtml(building.street)}, ${escapeHtml(building.postalCode)} ${escapeHtml(building.city)}</span>` +
          `<br><span style="color:#5c6a6b">${escapeHtml(typeLabel)}</span>`,
      );
      markers.push(marker);
    }

    // The container may not have its final size at init (the view was just
    // switched to "Karte"); invalidateSize + rAF makes fitBounds compute the
    // right zoom instead of a world-wide zoom-out.
    const frame = requestAnimationFrame(() => {
      map.invalidateSize();
      if (markers.length > 1) {
        map.fitBounds(L.latLngBounds(markers.map((marker) => marker.getLatLng())).pad(0.3));
      } else if (markers.length === 1) {
        map.setView(markers[0]!.getLatLng(), 14);
      }
    });

    return () => {
      cancelAnimationFrame(frame);
      map.remove();
    };
  }, [accountId, buildings]);

  const anyCoords = buildings.some((b) => b.latitude !== null && b.longitude !== null);

  return (
    <div className="relative">
      <div ref={containerRef} className="h-[520px] w-full overflow-hidden rounded-xl border border-mint" />
      {!anyCoords ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <p className="rounded-lg bg-white/90 px-4 py-2 text-sm text-slate shadow-sm">
            Für diese Objekte liegen noch keine Koordinaten vor.
          </p>
        </div>
      ) : null}
    </div>
  );
}
