import { RESULT_CARD } from './ScreeningResults';

export type CDLClassDistribution = {
  class_value: number;
  class_name?: string | null;
  pixel_count: number;
  share_pct: number;
};

export type CDLContextZone = {
  zone: string;
  status: string;
  classes: CDLClassDistribution[];
  total_pixel_count: number | null;
  nodata_pixel_count: number | null;
  coverage_pct: number | null;
  coverage_verified: boolean;
  product_vintage: string | null;
  vintage_verified: boolean;
  source: string | null;
  error_message: string | null;
};

export type CDLContextResult = {
  status: string;
  product_vintage: string | null;
  vintage_verified: boolean;
  aoi: CDLContextZone | null;
  one_mile_ring: CDLContextZone | null;
  thirty_meter_band: CDLContextZone | null;
  limitations: string[];
  error_message: string | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function isZone(value: unknown): value is CDLContextZone | null {
  if (value === null) return true;
  if (!isRecord(value)) return false;
  return (
    typeof value.zone === 'string' &&
    typeof value.status === 'string' &&
    Array.isArray(value.classes) &&
    value.classes.every(
      (item) =>
        isRecord(item) &&
        typeof item.class_value === 'number' &&
        typeof item.pixel_count === 'number' &&
        typeof item.share_pct === 'number',
    )
  );
}

export function parseCDLContextResult(value: unknown): CDLContextResult | null {
  let candidate = value;
  if (typeof candidate === 'string') {
    try {
      candidate = JSON.parse(candidate);
    } catch {
      return null;
    }
  }
  if (
    !isRecord(candidate) ||
    typeof candidate.status !== 'string' ||
    !Array.isArray(candidate.limitations) ||
    !candidate.limitations.every((item) => typeof item === 'string') ||
    !isZone(candidate.aoi) ||
    !isZone(candidate.one_mile_ring) ||
    !isZone(candidate.thirty_meter_band)
  ) {
    return null;
  }
  return candidate as unknown as CDLContextResult;
}

function reported(value: string | number | null | undefined): string {
  return value === null || value === undefined ? 'Not reported' : String(value);
}

function ZoneSummary({ title, zone }: { title: string; zone: CDLContextZone | null }) {
  return (
    <section className="grid gap-2 border-b border-border pb-3 last:border-b-0">
      <div>
        <h4 className="font-semibold text-sm">{title}</h4>
        {!zone ? (
          <p className="text-muted-foreground text-xs">No result was returned for this zone.</p>
        ) : (
          <dl className="grid grid-cols-2 gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted-foreground">Status</dt>
            <dd>{zone.status}</dd>
            <dt className="text-muted-foreground">Source</dt>
            <dd className="break-words">{reported(zone.source)}</dd>
            <dt className="text-muted-foreground">Vintage</dt>
            <dd>
              {reported(zone.product_vintage)}
              {zone.product_vintage
                ? zone.vintage_verified
                  ? ' (verified)'
                  : ' (not verified)'
                : ''}
            </dd>
            <dt className="text-muted-foreground">Coverage</dt>
            <dd>
              {reported(zone.coverage_pct)}
              {zone.coverage_pct === null || zone.coverage_pct === undefined ? '' : '%'}
              {zone.coverage_verified ? ' (verified)' : ' (not verified)'}
            </dd>
            <dt className="text-muted-foreground">Pixels / NoData</dt>
            <dd>
              {reported(zone.total_pixel_count)} / {reported(zone.nodata_pixel_count)}
            </dd>
          </dl>
        )}
      </div>
      {zone?.error_message && (
        <p className="text-destructive text-xs">{zone.error_message}</p>
      )}
      {zone && zone.classes.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-border text-muted-foreground">
                <th scope="col" className="py-1 pr-2">Class</th>
                <th scope="col" className="py-1 pr-2">Pixels</th>
                <th scope="col" className="py-1">Share</th>
              </tr>
            </thead>
            <tbody>
              {zone.classes.map((item, index) => (
                <tr key={`${item.class_value}-${index}`} className="border-b border-border/50">
                  <th scope="row" className="py-1 pr-2 font-normal">
                    {item.class_name ?? 'Name not reported'} (code {item.class_value})
                  </th>
                  <td className="py-1 pr-2">{item.pixel_count}</td>
                  <td className="py-1">{item.share_pct}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        zone && <p className="text-muted-foreground text-xs">No class distribution was returned.</p>
      )}
    </section>
  );
}

export function CDLContextSummary({ result }: { result: CDLContextResult }) {
  return (
    <div className={`${RESULT_CARD} grid gap-3`} data-testid="cdl-context-summary">
      <div>
        <h3 className="font-semibold text-sm">Preliminary CDL land-cover context</h3>
        <p className="mt-1 text-muted-foreground text-xs">
          Status: {result.status}. Vintage: {reported(result.product_vintage)}
          {result.product_vintage
            ? result.vintage_verified
              ? ' (verified)'
              : ' (not verified)'
            : ''}
        </p>
        <p className="mt-1 font-medium text-xs">
          Class shares are not official farmland classifications or perimeter-contact scores.
          This is preliminary context, not an official FPPA or LESA determination.
        </p>
      </div>
      <ZoneSummary title="AOI" zone={result.aoi} />
      <ZoneSummary title="One-mile exterior ring" zone={result.one_mile_ring} />
      <ZoneSummary title="30 m exterior band (near-perimeter proxy)" zone={result.thirty_meter_band} />
      {result.error_message && (
        <p className="text-destructive text-xs">{result.error_message}</p>
      )}
      <ul className="list-disc space-y-1 pl-5 text-muted-foreground text-xs">
        {result.limitations.map((limitation, index) => (
          <li key={`${index}-${limitation}`}>{limitation}</li>
        ))}
      </ul>
    </div>
  );
}
