// MapLibre GL JS 6 loads its worker from `./maplibre-gl-worker.mjs` next to
// `import.meta.url`. After the Vite build that URL is the app chunk, and Vite
// does not emit the worker file, so GeoJSON sources (Terra Draw layers) fail.
// Bundle the worker as its own asset and hand MapLibre its URL instead.
import { setWorkerUrl } from 'maplibre-gl';
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url';

setWorkerUrl(workerUrl);
