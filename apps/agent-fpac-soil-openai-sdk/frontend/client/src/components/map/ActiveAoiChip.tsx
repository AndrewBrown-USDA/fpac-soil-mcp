import { Button } from '@/components/ui/button';
import { useOptionalActiveAoi } from './ActiveAoiContext';

// Shows which map AOI goes with the next chat turn (ADR 0016); no coordinates.
export function ActiveAoiChip() {
  const context = useOptionalActiveAoi();
  const aoi = context?.activeAoi;
  if (!context || !aoi) return null;

  const acres = aoi.summary?.total_aoi_acres;
  const size =
    typeof acres === 'number' && Number.isFinite(acres)
      ? `${acres.toLocaleString(undefined, { maximumFractionDigits: 1 })} ac`
      : 'not screened';

  return (
    <div
      data-testid="active-aoi-chip"
      className="flex w-fit items-center gap-2 rounded-full border border-border bg-muted px-3 py-1 text-xs"
    >
      <span>
        Map AOI {aoi.aoi_ref}, {size}
      </span>
      <Button
        type="button"
        size="sm"
        variant="tertiary"
        className="h-5 px-1 text-xs"
        aria-label={`Detach map AOI ${aoi.aoi_ref} from this chat`}
        onClick={context.detach}
      >
        Detach
      </Button>
    </div>
  );
}
