import { Button } from '@/components/ui/button';
import { useOptionalActiveAoi } from './ActiveAoiContext';
import { useOptionalActiveCorridor } from './ActiveCorridorContext';

// Shows which map AOI goes with the next chat turn (ADR 0016); no coordinates.
export function ActiveAoiChip() {
  const context = useOptionalActiveAoi();
  const corridorContext = useOptionalActiveCorridor();
  const aoi = context?.activeAoi;
  const corridor = corridorContext?.activeCorridor;
  if (!aoi && !corridor) return null;

  const acres = aoi?.summary?.total_aoi_acres;
  const size =
    typeof acres === 'number' && Number.isFinite(acres)
      ? `${acres.toLocaleString(undefined, { maximumFractionDigits: 1 })} ac`
      : 'not screened';

  return (
    <div
      data-testid="active-geometry-chip"
      className="flex w-fit items-center gap-2 rounded-full border border-border bg-muted px-3 py-1 text-xs"
    >
      <span>
        {aoi ? `Map AOI ${aoi.aoi_ref}, ${size}` : `Corridor ${corridor?.corridor_ref}, attached to this chat`}
      </span>
      <Button
        type="button"
        size="sm"
        variant="tertiary"
        className="h-5 px-1 text-xs"
        aria-pressed
        aria-label={aoi
          ? `Detach map AOI ${aoi.aoi_ref} from this chat`
          : `Detach corridor ${corridor?.corridor_ref} from this chat`}
        onClick={aoi ? context?.detach : corridorContext?.detach}
      >
        Detach
      </Button>
    </div>
  );
}
