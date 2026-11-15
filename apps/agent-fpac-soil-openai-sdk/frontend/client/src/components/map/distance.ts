import type { Position } from './geojson';

export type DistanceUnit = 'meters' | 'kilometers' | 'miles';

// Haversine distance on a spherical Earth (mean radius); elevation is ignored.
export function lineDistance(points: readonly Position[], unit: DistanceUnit): number {
  const radians = (degrees: number) => (degrees * Math.PI) / 180;
  let meters = 0;
  for (let index = 1; index < points.length; index += 1) {
    const [lon1, lat1] = points[index - 1];
    const [lon2, lat2] = points[index];
    if (![lon1, lat1, lon2, lat2].every(Number.isFinite)) return 0;
    const dLat = radians(lat2 - lat1);
    const dLon = radians(lon2 - lon1);
    const a = Math.sin(dLat / 2) ** 2 + Math.cos(radians(lat1)) * Math.cos(radians(lat2)) * Math.sin(dLon / 2) ** 2;
    meters += 6371008.8 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  }
  return unit === 'kilometers' ? meters / 1000 : unit === 'miles' ? meters / 1609.344 : meters;
}
