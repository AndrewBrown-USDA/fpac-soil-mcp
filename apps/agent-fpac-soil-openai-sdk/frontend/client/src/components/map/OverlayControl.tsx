import { CONTEXT_LABEL, OVERLAYS } from './overlays';
import type { Overlay, OverlayId } from './overlays';

export type OverlayFlags = Record<OverlayId, boolean>;

export const NO_OVERLAYS: OverlayFlags = { ssurgo: false, counties: false, urban: false };

function statusText(
  overlay: Overlay,
  zoom: number,
  error: boolean,
  loading: boolean,
): string {
  if (zoom < overlay.minzoom) return 'Zoom in to see';
  if (error) return 'Could not load this layer';
  if (loading) return 'Loading';
  return 'Shown';
}

// Context layers, all off by default. Native checkboxes keep the control keyboard and
// screen-reader friendly; collapsed by default so it does not take map height.
export function OverlayControl({
  on,
  errors,
  loading,
  zoom,
  onToggle,
}: {
  on: OverlayFlags;
  errors: OverlayFlags;
  loading: OverlayFlags;
  zoom: number;
  onToggle: (id: OverlayId, next: boolean) => void;
}) {
  const count = OVERLAYS.filter((overlay) => on[overlay.id]).length;
  return (
    <details className="rounded-md border border-border px-2 py-1 text-sm">
      <summary className="cursor-pointer font-medium">
        Context layers{count > 0 ? ` (${count} on)` : ''}
      </summary>
      <fieldset className="mt-1 grid gap-2">
        <legend className="sr-only">Context layers</legend>
        {OVERLAYS.map((overlay) => {
          const inputId = `overlay-toggle-${overlay.id}`;
          const status = on[overlay.id]
            ? statusText(overlay, zoom, errors[overlay.id], loading[overlay.id])
            : null;
          return (
            <div key={overlay.id} className="flex items-start gap-2">
              <input
                id={inputId}
                type="checkbox"
                className="mt-1"
                checked={on[overlay.id]}
                onChange={(event) => onToggle(overlay.id, event.target.checked)}
              />
              <label htmlFor={inputId} className="flex flex-col">
                <span>
                  {overlay.title}
                  {status && (
                    <span
                      className={`ml-2 text-xs ${status === 'Could not load this layer' ? 'text-destructive' : 'text-muted-foreground'}`}
                      aria-live="polite"
                    >
                      ({status})
                    </span>
                  )}
                </span>
                <span className="text-muted-foreground text-xs">
                  {CONTEXT_LABEL}. Source: {overlay.source} ({overlay.vintage}).
                </span>
              </label>
            </div>
          );
        })}
      </fieldset>
    </details>
  );
}
