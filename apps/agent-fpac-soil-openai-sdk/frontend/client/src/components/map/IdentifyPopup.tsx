import { useState } from 'react';
import { Button } from '@/components/ui/button';
import type { AreaInfo, SoilInfo } from './identify';
import { CONTEXT_LABEL } from './overlays';
import type { Overlay } from './overlays';

export type IdentifySection =
  | { overlay: Overlay; state: 'loading' }
  | { overlay: Overlay; state: 'error' }
  | { overlay: Overlay; state: 'done'; soil?: SoilInfo | null; area?: AreaInfo | null };

export type UseAsAoiResult = { ok: true } | { ok: false; message: string };

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  if (!value) return null;
  return (
    <div>
      <span className="text-muted-foreground">{label}: </span>
      {value}
    </div>
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

// One section per overlay that was on at the clicked point. Rendered into the MapLibre
// popup through a portal.
export function IdentifyPopup({
  sections,
  onUseAsAoi,
}: {
  sections: IdentifySection[];
  onUseAsAoi: (section: IdentifySection, area: AreaInfo) => Promise<UseAsAoiResult>;
}) {
  return (
    <div className="flex max-w-72 flex-col gap-2 text-foreground text-xs">
      {sections.map((section) => (
        <section key={section.overlay.id} aria-label={section.overlay.title}>
          <h3 className="font-medium text-sm">{section.overlay.title}</h3>
          {section.state === 'loading' && <p className="text-muted-foreground">Loading...</p>}
          {section.state === 'error' && (
            <p className="text-destructive">Could not load this layer here.</p>
          )}
          {section.state === 'done' && section.soil && (
            <>
              <Field label="Map unit symbol" value={section.soil.musym} />
              <Field label="Map unit key (mukey)" value={section.soil.mukey} />
              <Field label="Survey area" value={section.soil.areasymbol} />
              <Field label="Polygon acres" value={section.soil.acres} />
              <p className="mt-1 text-muted-foreground">
                Farmland class and map unit name are not in this service; run screening for
                this area.
              </p>
            </>
          )}
          {section.state === 'done' && section.area && (
            <>
              <Field label="Name" value={section.area.name} />
              <Field label="GEOID" value={section.area.geoid} />
              <AreaActions section={section} area={section.area} onUseAsAoi={onUseAsAoi} />
            </>
          )}
          {section.state === 'done' && !section.soil && !section.area && (
            <p className="text-muted-foreground">Nothing here.</p>
          )}
          <p className="mt-1 text-muted-foreground">
            {CONTEXT_LABEL}. {section.overlay.source} ({section.overlay.vintage}).
          </p>
        </section>
      ))}
    </div>
  );
}
