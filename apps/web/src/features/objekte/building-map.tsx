'use client';

import { useEffect, useMemo, useRef, useState } from 'react';

import type { BuildingSummary } from '@/lib/contracts';

export function buildingTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    WOHN_UND_GESCHAEFTSHAUS: 'Wohn- und Geschäftshaus',
    WOHNHAUS: 'Wohnhaus',
    GEWERBEIMMOBILIE: 'Gewerbeimmobilie',
    EINFAMILIENHAUS: 'Einfamilienhaus',
  };
  return labels[value] ?? value;
}

export interface BuildingMapEntry {
  id: string;
  name: string;
  href: string;
  address: string;
  typeLabel: string;
  latitude: number;
  longitude: number;
}

export function buildMapEntries(
  accountId: string,
  buildings: BuildingSummary[],
): BuildingMapEntry[] {
  return buildings.flatMap((building) => {
    if (building.latitude === null || building.longitude === null) return [];
    return [
      {
        id: building.id,
        name: building.name,
        href: `/a/${accountId}/objekte/${building.id}`,
        address: `${building.street}, ${building.postalCode} ${building.city}`,
        typeLabel: buildingTypeLabel(building.buildingType),
        latitude: building.latitude,
        longitude: building.longitude,
      },
    ];
  });
}

function assetUrl(asset: string | { src: string }): string {
  return typeof asset === 'string' ? asset : asset.src;
}

export function BuildingMap({
  accountId,
  buildings,
}: {
  accountId: string;
  buildings: BuildingSummary[];
}) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mapFailed, setMapFailed] = useState(false);
  const entries = useMemo(() => buildMapEntries(accountId, buildings), [accountId, buildings]);

  useEffect(() => {
    if (entries.length === 0 || containerRef.current === null) return;

    let disposed = false;
    let map: { remove: () => void } | undefined;

    async function initializeMap() {
      const L = await import('leaflet');
      const [markerIcon, markerIcon2x, markerShadow] = await Promise.all([
        import('leaflet/dist/images/marker-icon.png'),
        import('leaflet/dist/images/marker-icon-2x.png'),
        import('leaflet/dist/images/marker-shadow.png'),
      ]);
      if (disposed || containerRef.current === null) return;

      const marker = L.icon({
        iconUrl: assetUrl(markerIcon.default),
        iconRetinaUrl: assetUrl(markerIcon2x.default),
        shadowUrl: assetUrl(markerShadow.default),
        iconSize: [25, 41],
        iconAnchor: [12, 41],
        popupAnchor: [1, -34],
        shadowSize: [41, 41],
      });
      const leafletMap = L.map(containerRef.current, { scrollWheelZoom: false });
      map = leafletMap;

      if (process.env.NEXT_PUBLIC_OSM_TILES_ENABLED === 'true') {
        L.tileLayer(
          process.env.NEXT_PUBLIC_OSM_TILE_URL ?? 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
          { attribution: '© OpenStreetMap-Mitwirkende', maxZoom: 19 },
        ).addTo(leafletMap);
      }

      const points: Array<[number, number]> = [];
      for (const entry of entries) {
        const point: [number, number] = [entry.latitude, entry.longitude];
        points.push(point);
        const popup = document.createElement('div');
        const link = document.createElement('a');
        link.href = entry.href;
        link.textContent = entry.name;
        link.className = 'font-semibold';
        const address = document.createElement('p');
        address.textContent = entry.address;
        address.className = 'text-slate';
        const type = document.createElement('p');
        type.textContent = entry.typeLabel;
        type.className = 'text-slate';
        popup.append(link, address, type);
        L.marker(point, { icon: marker }).addTo(leafletMap).bindPopup(popup);
      }

      if (points.length === 1 && points[0]) {
        leafletMap.setView(points[0], 14);
      } else {
        leafletMap.fitBounds(points, { padding: [32, 32], maxZoom: 15 });
      }
    }

    void initializeMap().catch(() => {
      if (!disposed) setMapFailed(true);
    });
    return () => {
      disposed = true;
      map?.remove();
    };
  }, [entries]);

  if (entries.length === 0) {
    return (
      <div
        role="region"
        aria-label="Objektkarte"
        className="flex min-h-80 items-center justify-center rounded-xl border border-slate/30 bg-mint/40 p-8 text-center text-slate"
      >
        Für diese Objekte liegen noch keine Koordinaten vor.
      </div>
    );
  }

  return (
    <div role="region" aria-label="Objektkarte" className="relative">
      <div
        ref={containerRef}
        className="h-[min(520px,65vh)] min-h-80 w-full rounded-xl border border-slate/30"
      />
      <ul className="sr-only">
        {entries.map((entry) => (
          <li key={entry.id}>{entry.name}</li>
        ))}
      </ul>
      {mapFailed ? (
        <p role="status" className="mt-3 text-sm text-slate">
          Die Karte konnte nicht geladen werden. Die Objektliste bleibt verfügbar.
        </p>
      ) : null}
    </div>
  );
}
