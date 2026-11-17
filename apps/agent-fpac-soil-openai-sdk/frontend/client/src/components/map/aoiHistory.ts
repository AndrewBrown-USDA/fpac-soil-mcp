// One-level AOI undo (issue #89 C). Every change keeps the full previous AOI
// context (ref, geometry, summary), so Undo restores it as it was, under the same
// reference. Clear and Detach are changes too, so they can be undone.
export type AoiHistory<T> = { aoi: T | null; previous: T | null };

export function replaceAoi<T>(history: AoiHistory<T>, next: T | null): AoiHistory<T> {
  if (!history.aoi && !next) return history;
  return { aoi: next, previous: history.aoi };
}

export function undoAoi<T>(history: AoiHistory<T>): AoiHistory<T> {
  if (!history.previous) return history;
  return { aoi: history.previous, previous: null };
}
