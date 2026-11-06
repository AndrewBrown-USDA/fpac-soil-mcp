import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { AreaInfo, SoilInfo } from './identify';
import type { Overlay } from './overlays';

export type IdentifySection =
  | { overlay: Overlay; state: 'loading' }
  | { overlay: Overlay; state: 'error' }
  | { overlay: Overlay; state: 'done'; soil?: SoilInfo | null; area?: AreaInfo | null };

export type UseAsAoiResult = { ok: true } | { ok: false; message: string };

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
  sections,
  onUseAsAoi,
}: {
  sections: IdentifySection[];
  onUseAsAoi: (section: IdentifySection, area: AreaInfo) => Promise<UseAsAoiResult>;
}) {
  return (
    <div className="flex max-h-64 w-60 flex-col gap-2 overflow-y-auto rounded-md border border-border bg-popover p-2 pr-6 text-popover-foreground text-xs shadow-md">
      {sections.map((section) => (
        <section key={section.overlay.id} aria-label={section.overlay.title}>
          <h3 className="font-medium">{section.overlay.title}</h3>
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
      <p className="text-muted-foreground">Context layers, not analysis results.</p>
    </div>
  );
}
