import type { PolygonGeometry } from './geojson';

export function serializeAoiGeoJson(geometry: PolygonGeometry, label: string): string {
  return JSON.stringify({
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        properties: label.trim() ? { label: label.trim() } : {},
        geometry,
      },
    ],
  }, null, 2);
}

export function aoiFilename(label: string): string {
  const safe = label.trim().replace(/[^\w-]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 64);
  return `${safe || 'aoi'}.geojson`;
}
