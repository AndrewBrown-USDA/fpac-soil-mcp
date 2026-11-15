import assert from 'node:assert/strict';
import test from 'node:test';
import { NO_OVERLAYS } from './OverlayControl';
import { OVERLAYS, overlayIdForSource, overlaySourceId } from './overlays';

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
