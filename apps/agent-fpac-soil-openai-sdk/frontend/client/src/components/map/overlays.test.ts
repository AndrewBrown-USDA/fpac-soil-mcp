import assert from 'node:assert/strict';
import test from 'node:test';
import { NO_OVERLAYS } from './OverlayControl';
import {
  normalizeOverlayOrder,
  OVERLAYS,
  overlayIdForSource,
  overlaySourceId,
  reorderOverlays,
  restoreOverlayOrder,
} from './overlays';

test('NAIP uses the fixed ImageServer exportImage request and maps its source id', () => {
  const naip = OVERLAYS.find((overlay) => overlay.id === 'naip');
  assert.ok(naip);
  assert.equal(
    naip.tiles,
    'https://imagery.nationalmap.gov/arcgis/rest/services/USGSNAIPImagery/ImageServer/exportImage?bbox={bbox-epsg-3857}&bboxSR=3857&imageSR=3857&size=256,256&format=png32&f=image',
  );
  assert.equal(naip.tiles.includes('/tile/'), false);
  assert.equal(naip.attribution, 'USGS, USDA, The National Map: Orthoimagery');
  assert.match(naip.vintage, /dates vary by location/);
  assert.equal(NO_OVERLAYS.naip, false);
  assert.equal(overlaySourceId('naip'), 'overlay-naip');
  assert.equal(overlayIdForSource('overlay-naip'), 'naip');
  assert.equal(overlayIdForSource('overlay-unknown'), null);
});

test('overlay order restores valid catalog order and defaults missing or malformed data', () => {
  assert.deepEqual(normalizeOverlayOrder(['naip', 'cdl', 'naip', 'unknown']), [
    'naip', 'cdl', 'ssurgo', 'counties', 'urban',
  ]);
  assert.deepEqual(restoreOverlayOrder(null), OVERLAYS.map(({ id }) => id));
  assert.deepEqual(restoreOverlayOrder('{bad'), OVERLAYS.map(({ id }) => id));
  assert.deepEqual(normalizeOverlayOrder(['new-layer', 'cdl']), [
    'cdl', 'ssurgo', 'counties', 'urban', 'naip',
  ]);
});

test('raster reordering retains every raster below result vectors and AOI', () => {
  const layers = ['background', 'overlay-naip', 'result-fill-a', 'overlay-cdl', 'result-line-a', 'aoi-line'];
  const map = {
    getStyle: () => ({ layers: layers.map((id) => ({ id })) }),
    getLayer: (id: string) => layers.includes(id) ? { id } : undefined,
    moveLayer: (id: string, before?: string) => {
      layers.splice(layers.indexOf(id), 1);
      const index = before ? layers.indexOf(before) : layers.length;
      layers.splice(index, 0, id);
    },
  };

  reorderOverlays(map as never, ['naip', 'cdl', 'ssurgo', 'counties', 'urban']);

  assert.deepEqual(layers, [
    'background', 'overlay-cdl', 'overlay-naip', 'result-fill-a', 'result-line-a', 'aoi-line',
  ]);
});
