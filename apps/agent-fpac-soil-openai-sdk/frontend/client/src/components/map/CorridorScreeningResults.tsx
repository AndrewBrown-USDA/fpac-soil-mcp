import { RESULT_CARD, RegulatoryNotice } from './ScreeningResults';
import type { CorridorDisplay, CorridorScreeningResponse } from './useCorridorScreening';

function number(value: unknown): string | null {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString(undefined, { maximumFractionDigits: 1 })
    : null;
}

function Summary({ display }: { display: CorridorDisplay }) {
  const fields = [
    ['Direct impact', display.impact_breakdown.direct_acres, ' ac'],
    ['Indirect impact', display.impact_breakdown.indirect_acres, ' ac'],
    ['Total project area', display.impact_breakdown.total_project_acres, ' ac'],
    ['Relative rating', display.composite_relative_rating, ''],
  ] as const;
  const shown = fields.filter(([, value]) => number(value) !== null);
  return (
    <section aria-label="Corridor screening summary" className={RESULT_CARD}>
      <span className="rounded-full border border-[var(--border-warning)] bg-[var(--background-warning)] px-2 py-0.5 font-medium text-xs">
        Preliminary screening estimate
      </span>
      <dl className="mt-2 grid grid-cols-[repeat(auto-fit,minmax(8rem,1fr))] gap-3">
        {shown.map(([label, value, suffix]) => (
          <div key={label} className="flex flex-col">
            <dt className="text-muted-foreground text-xs">{label}</dt>
            <dd className="font-semibold tabular-nums">{number(value)}{suffix}</dd>
          </div>
        ))}
      </dl>
      {display.county_segments.length > 0 && <div className="mt-3 grid gap-1 text-sm">
        {display.county_segments.map((segment, index) => <p key={`${segment.county_name}-${index}`}>
          {[segment.county_name, segment.state_name].filter(Boolean).join(', ')}: {number(segment.total_segment_acres)} ac
        </p>)}
      </div>}
      {display.alternatives.length > 0 && <div className="mt-3 grid gap-1 text-sm">
        {display.alternatives.map((alternative, index) => <p key={`${alternative.alternative_id}-${index}`}>
          {alternative.alternative_id ?? `Alternative ${index + 1}`}: {number(alternative.total_project_acres)} ac
        </p>)}
      </div>}
    </section>
  );
}

export function CorridorScreeningResults({ result }: { result: CorridorScreeningResponse }) {
  return (
    <div className="flex flex-col gap-3">
      <Summary display={result.display} />
      <RegulatoryNotice notice={result.regulatory_notice} />
    </div>
  );
}
