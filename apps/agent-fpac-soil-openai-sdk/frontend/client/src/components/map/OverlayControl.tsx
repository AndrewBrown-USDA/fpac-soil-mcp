import { Layers } from 'lucide-react';
import { useState } from 'react';
import {
  CONTEXT_LABEL,
  NAIP_AVAILABILITY,
  OVERLAYS,
  OVERLAY_ORDER_EVENT,
  OVERLAY_ORDER_STORAGE_KEY,
  normalizeOverlayOrder,
  restoreOverlayOrder,
} from './overlays';
import type { Overlay, OverlayId, OverlayOrder } from './overlays';

export type OverlayFlags = Record<OverlayId, boolean>;

export const NO_OVERLAYS: OverlayFlags = {
  ssurgo: false,
  counties: false,
  urban: false,
  cdl: false,
  naip: false,
};

function savedOrder(): OverlayOrder {
  try {
    return restoreOverlayOrder(
      typeof window === 'undefined' ? null : window.localStorage.getItem(OVERLAY_ORDER_STORAGE_KEY),
    );
  } catch {
    return restoreOverlayOrder(null);
  }
}

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

// Context layers, all off by default: a "Layers" button floating in the map's top-right
// corner that opens the toggles. Native <details> and checkboxes keep it keyboard and
// screen-reader friendly. `open` is controlled so the map can open it from a hint.
export function OverlayControl({
  on,
  errors,
  loading,
  zoom,
  open,
  onOpenChange,
  onToggle,
}: {
  on: OverlayFlags;
  errors: OverlayFlags;
  loading: OverlayFlags;
  zoom: number;
  open: boolean;
  onOpenChange: (next: boolean) => void;
  onToggle: (id: OverlayId, next: boolean) => void;
}) {
  const [order, setOrder] = useState<OverlayOrder>(savedOrder);
  const count = OVERLAYS.filter((overlay) => on[overlay.id]).length;

  function moveOverlay(id: OverlayId, direction: -1 | 1) {
    const next = [...order];
    const index = next.indexOf(id);
    const target = index + direction;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    const normalized = normalizeOverlayOrder(next);
    setOrder(normalized);
    try {
      window.localStorage.setItem(OVERLAY_ORDER_STORAGE_KEY, JSON.stringify(normalized));
    } catch {
      // Keep the current session's ordering even when browser storage is unavailable.
    }
    window.dispatchEvent(new CustomEvent(OVERLAY_ORDER_EVENT, { detail: normalized }));
  }

  return (
    <details
      open={open}
      onToggle={(event) => onOpenChange(event.currentTarget.open)}
      className="absolute top-2 right-2 z-10 max-w-[16rem] rounded-md border border-border bg-popover text-popover-foreground text-sm shadow-md"
    >
      <summary className="flex cursor-pointer list-none items-center gap-1.5 px-2 py-1 font-medium [&::-webkit-details-marker]:hidden">
        <Layers className="size-4" aria-hidden="true" />
        Layers{count > 0 ? ` (${count} on)` : ''}
      </summary>
      <fieldset className="grid gap-2 border-border border-t px-2 py-2">
        <legend className="sr-only">Context layers</legend>
        {order.map((overlayId, index) => {
          const overlay = OVERLAYS.find(({ id }) => id === overlayId);
          if (!overlay) return null;
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
                  {overlay.id === 'naip' && ` ${NAIP_AVAILABILITY}`}
                </span>
              </label>
              <span className="ml-auto flex gap-1">
                <button
                  type="button"
                  aria-label={`Move ${overlay.title} up`}
                  disabled={index === 0}
                  onClick={() => moveOverlay(overlay.id, -1)}
                >
                  ↑
                </button>
                <button
                  type="button"
                  aria-label={`Move ${overlay.title} down`}
                  disabled={index === order.length - 1}
                  onClick={() => moveOverlay(overlay.id, 1)}
                >
                  ↓
                </button>
              </span>
            </div>
          );
        })}
      </fieldset>
    </details>
  );
}
