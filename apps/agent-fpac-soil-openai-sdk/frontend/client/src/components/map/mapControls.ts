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

type DrawFeatureLike = { id?: string | number; properties?: Record<string, unknown> | null };

// One AOI at a time: after a new shape is drawn, the previous AOI shapes go.
// An Edit (select-mode) finish removes nothing: Terra Draw 1.39 fires finish for
// drag, midpoint insert and vertex delete, and its own selection-point and
// midpoint features are in the snapshot (issue #89 A).
export function aoiFeaturesToRemove(
  snapshot: DrawFeatureLike[],
  finishedId: string | number,
  context: { mode: string },
): Array<string | number> {
  if (context.mode === 'select') return [];
  return snapshot.flatMap((feature) =>
    feature.id !== undefined &&
    feature.id !== finishedId &&
    (feature.properties?.mode === 'polygon' || feature.properties?.mode === 'rectangle')
      ? [feature.id]
      : [],
  );
}

export type MeasurementMode = 'static' | 'measure';

export function measurementModeAfterCancel(): MeasurementMode {
  return 'static';
}
