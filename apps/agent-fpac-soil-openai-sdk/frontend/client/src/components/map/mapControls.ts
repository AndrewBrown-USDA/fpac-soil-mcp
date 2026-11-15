import type { PolygonGeometry } from './geojson';
import { geometryBounds } from './geojson';

export const INITIAL_MAP_VIEW = { center: [-98, 39] as [number, number], zoom: 3 };

export function aoiViewBounds(geometry: PolygonGeometry | null) {
  return geometry ? geometryBounds(geometry) : null;
}

export function setLayerVisibility(
  setLayoutProperty: (id: string, property: 'visibility', value: 'visible' | 'none') => void,
  layerIds: readonly string[], visible: boolean,
) {
  for (const id of layerIds) setLayoutProperty(id, 'visibility', visible ? 'visible' : 'none');
}

export type MeasurementMode = 'static' | 'measure';

export function measurementModeAfterCancel(): MeasurementMode {
  return 'static';
}
