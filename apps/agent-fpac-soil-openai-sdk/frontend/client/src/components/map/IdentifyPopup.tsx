import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { geometryBounds, toPolygonGeometry } from './geojson';
import type { PolygonGeometry } from './geojson';
import { fetchOutline } from './identify';
import type { AreaInfo, AreaOverlayId, SoilInfo } from './identify';
import type { Overlay } from './overlays';

export type IdentifySection =
  | { overlay: Overlay; state: 'loading' }
  | { overlay: Overlay; state: 'error' }
  | {
      overlay: Overlay;
      state: 'done';
      soil?: SoilInfo | null;
      area?: AreaInfo | null;
      areaGeometry?: PolygonGeometry | null;
    };

export type UseAreaGeometry = (
  section: IdentifySection,
  area: AreaInfo,
  geometry: PolygonGeometry,
) => { ok: boolean; message?: string } | undefined;

// A clicked result polygon: the server's feature properties (ADR 0017, Plan 44 A7),
// shown as sent.
export type ResultInfo = {
  muname: string | null;
  musym: string | null;
  farmlndcl: string | null;
  acres: string | null;
  productivity: string | null;
  productivitySource: string | null;
  alignment: string | null;
};

function text(value: unknown): string | null {
  if (typeof value === 'string') return value.trim() || null;
  if (typeof value === 'number' && Number.isFinite(value)) return String(value);
  return null;
}

export function resultInfo(props: Record<string, unknown> | null | undefined): ResultInfo | null {
  if (!props) return null;
  const rating = text(props.productivity_rating);
  const ratingClass = text(props.productivity_rating_class);
  return {
    muname: text(props.muname),
    musym: text(props.musym),
    farmlndcl: text(props.farmlndcl),
    acres: text(props.area_ac),
    productivity: rating ? (ratingClass ? `${rating} (${ratingClass})` : rating) : null,
    productivitySource: rating ? text(props.productivity_rating_source) : null,
    alignment: text(props.alignment),
  };
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <>
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="truncate">{value}</dd>
    </>
  );
}

function AreaActions({
  section,
  area,
  onUseGeometry,
}: {
  section: IdentifySection;
  area: AreaInfo;
  onUseGeometry: UseAreaGeometry;
}) {
  const exact = section.state === 'done' ? (section.areaGeometry ?? null) : null;
  const validExact = exact ? toPolygonGeometry(exact) : null;
  const [actionError, setActionError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const chooseGeometry = async (kind: 'exact' | 'bbox') => {
    if (busy) return;
    setBusy(true);
    setActionError(null);
    try {
      const outline = validExact
        ? { geometry: validExact }
        : await fetchOutline(section.overlay.id as AreaOverlayId, area.geoid, new AbortController().signal);
      if (!outline) throw new Error('TIGERweb did not return a usable polygon outline.');
      const geometry = outline.geometry;
      const selected =
        kind === 'exact'
          ? geometry
          : (() => {
              const bounds = geometryBounds(geometry);
              if (!bounds) throw new Error('Could not calculate a bounding box for this outline.');
              return {
                type: 'Polygon' as const,
                coordinates: [[
                  [bounds[0][0], bounds[0][1]],
                  [bounds[1][0], bounds[0][1]],
                  [bounds[1][0], bounds[1][1]],
                  [bounds[0][0], bounds[1][1]],
                  [bounds[0][0], bounds[0][1]],
                ]],
              };
            })();
      const result = onUseGeometry(section, area, selected);
      if (result && !result.ok) setActionError(result.message ?? `Could not use this ${kind} geometry.`);
    } catch (error) {
      setActionError(error instanceof Error ? error.message : 'Could not load the outline.');
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="mt-1 flex gap-1" role="group" aria-label={`Use ${area.name} as area of interest`}>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        onClick={() => void chooseGeometry('exact')}
        disabled={busy}
        title="Use the exact polygon as the AOI"
        aria-label={`Use exact polygon for ${area.name} as AOI`}
        className="h-7 px-2 text-xs"
      >
        Exact
      </Button>
      <Button
        type="button"
        size="sm"
        variant="secondary"
        onClick={() => void chooseGeometry('bbox')}
        disabled={busy}
        title="Use the bounding box as the AOI"
        aria-label={`Use bounding box for ${area.name} as AOI`}
        className="h-7 px-2 text-xs"
      >
        BBOX
      </Button>
      {actionError && <p role="alert" className="text-destructive">{actionError}</p>}
    </div>
  );
}

// One compact section per overlay that was on at the clicked point, rendered into the
// MapLibre popup through a portal. Theme colours come from the app (`bg-popover`), so
// the popup follows light and dark mode; MapLibre's own white box is cleared in
// MapPanel.
export function IdentifyPopup({
  result,
  sections,
  onUseGeometry,
}: {
  result: ResultInfo | null;
  sections: IdentifySection[];
  onUseGeometry: UseAreaGeometry;
}) {
  return (
    <div className="flex max-h-64 w-60 flex-col gap-2 overflow-y-auto rounded-md border border-border bg-popover p-2 pr-6 text-popover-foreground text-xs shadow-md">
      {result && (
        <section aria-label="Result">
          <h3 className="font-semibold text-xs leading-tight">Result: map unit</h3>
          {result.muname && <p>{result.muname}</p>}
          <dl className="grid grid-cols-[auto_1fr] gap-x-2">
            <Row label="Symbol" value={result.musym} />
            <Row label="Farmland" value={result.farmlndcl} />
            <Row label="Acres" value={result.acres} />
            <Row label="Productivity" value={result.productivity} />
            <Row label="Index" value={result.productivitySource} />
            <Row label="Alignment" value={result.alignment} />
          </dl>
        </section>
      )}
      {sections.map((section) => (
        <section key={section.overlay.id} aria-label={section.overlay.title}>
          {/* Explicit size: index.css gives bare h3 a larger base size. */}
          <h3 className="font-semibold text-xs leading-tight">{section.overlay.title}</h3>
          {section.state === 'loading' && <p className="text-muted-foreground">Loading...</p>}
          {section.state === 'error' && <p className="text-destructive">Could not load.</p>}
          {section.state === 'done' && section.soil && (
            <>
              <dl className="grid grid-cols-[auto_1fr] gap-x-2">
                <Row label="Symbol" value={section.soil.musym} />
                <Row label="mukey" value={section.soil.mukey} />
                <Row label="Survey" value={section.soil.areasymbol} />
              </dl>
              <p className="text-muted-foreground">Run screening for farmland class.</p>
            </>
          )}
          {section.state === 'done' && section.area && (
              <div className="flex items-start gap-2">
                <dl className="grid min-w-0 flex-1 grid-cols-[auto_1fr] gap-x-2">
                  <Row label="Name" value={section.area.name} />
                  <Row label="GEOID" value={section.area.geoid} />
                </dl>
                <AreaActions section={section} area={section.area} onUseGeometry={onUseGeometry} />
              </div>
          )}
          {section.state === 'done' && !section.soil && !section.area && (
            <p className="text-muted-foreground">Nothing here.</p>
          )}
        </section>
      ))}
    </div>
  );
}
