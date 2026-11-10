import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { AreaInfo, SoilInfo } from './identify';
import type { Overlay } from './overlays';

export type IdentifySection =
  | { overlay: Overlay; state: 'loading' }
  | { overlay: Overlay; state: 'error' }
  | { overlay: Overlay; state: 'done'; soil?: SoilInfo | null; area?: AreaInfo | null };

export type UseAsAoiResult = { ok: true } | { ok: false; message: string };

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
  onUseAsAoi,
}: {
  section: IdentifySection;
  area: AreaInfo;
  onUseAsAoi: (section: IdentifySection, area: AreaInfo) => Promise<UseAsAoiResult>;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const run = async () => {
    setBusy(true);
    setMessage(null);
    const result = await onUseAsAoi(section, area);
    setBusy(false);
    if (!result.ok) setMessage(result.message);
  };
  return (
    <div className="mt-1 flex flex-col gap-1">
      <Button type="button" size="sm" variant="secondary" onClick={run} disabled={busy}>
        {busy ? 'Loading outline...' : 'Use as AOI'}
      </Button>
      {message && (
        <p role="alert" className="text-destructive">
          {message}
        </p>
      )}
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
  onUseAsAoi,
}: {
  result: ResultInfo | null;
  sections: IdentifySection[];
  onUseAsAoi: (section: IdentifySection, area: AreaInfo) => Promise<UseAsAoiResult>;
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
          <p className="text-muted-foreground">Preliminary machine estimate.</p>
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
            <>
              <dl className="grid grid-cols-[auto_1fr] gap-x-2">
                <Row label="Name" value={section.area.name} />
                <Row label="GEOID" value={section.area.geoid} />
              </dl>
              <AreaActions section={section} area={section.area} onUseAsAoi={onUseAsAoi} />
            </>
          )}
          {section.state === 'done' && !section.soil && !section.area && (
            <p className="text-muted-foreground">Nothing here.</p>
          )}
        </section>
      ))}
      {sections.length > 0 && (
        <p className="text-muted-foreground">Context layers, not analysis results.</p>
      )}
    </div>
  );
}
