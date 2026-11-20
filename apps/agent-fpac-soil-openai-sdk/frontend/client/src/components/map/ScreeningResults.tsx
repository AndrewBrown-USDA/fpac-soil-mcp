import { ResultsTable } from './ResultsTable';
import type { DisplayAnalysis, ScreeningResponse } from './useScreening';

const FARMLAND_LAYER_ID = 'farmland_classes';

// Shared look for the result sections (also used by the tool-result view).
export const RESULT_CARD = 'rounded-md border border-border bg-card p-3';
export const NOTICE_CARD =
  'rounded-md border border-border border-l-4 border-l-atlas-soil bg-muted p-3 text-sm';

function num(value: unknown): number | null {
  return typeof value === 'number' && Number.isFinite(value) ? value : null;
}

function fmt(value: number): string {
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 });
}

// Headline figures exactly as the server returned them; nothing is computed here,
// and missing values are left out rather than shown as zero.
function SummaryStrip({ analysis }: { analysis: DisplayAnalysis }) {
  const summary = analysis.farmland_summary ?? {};
  const aoiAcres = num(analysis.total_aoi_acres);
  const protectedAcres = num(summary.total_fppa_protected_acres);
  const protectedPct = num(summary.total_fppa_protected_pct);
  const coverage = analysis.coverage_status || null;
  const items: Array<{ label: string; value: string }> = [];
  if (aoiAcres !== null) items.push({ label: 'AOI', value: `${fmt(aoiAcres)} ac` });
  if (protectedAcres !== null || protectedPct !== null) {
    const parts = [
      protectedAcres !== null ? `${fmt(protectedAcres)} ac` : null,
      protectedPct !== null ? `${fmt(protectedPct)}%` : null,
    ].filter(Boolean);
    items.push({ label: 'FPPA-protected farmland', value: parts.join(' / ') });
  }
  if (coverage) items.push({ label: 'Coverage', value: coverage });
  if (items.length === 0) return null;
  return (
    <section aria-label="Screening summary" className={RESULT_CARD}>
      <dl className="grid grid-cols-[repeat(auto-fit,minmax(8rem,1fr))] gap-3">
        {items.map((item) => (
          <div key={item.label} className="flex flex-col">
            <dt className="text-muted-foreground text-xs">{item.label}</dt>
            <dd className="font-semibold text-base tabular-nums">{item.value}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

// Verbatim regulatory notice collapsed to reduce visual dominance while
// remaining available. A missing notice is flagged as an invalid result (ADR 0003).
export function RegulatoryNotice({ notice }: { notice: string | null }) {
  if (!notice) {
    return (
      <p role="alert" className="text-destructive text-sm">
        Regulatory notice missing - treat this result as invalid.
      </p>
    );
  }
  return (
    <details className={NOTICE_CARD}>
      <summary className="cursor-pointer font-semibold text-sm">Regulatory notice</summary>
      <p className="mt-2 whitespace-pre-line text-xs">{notice}</p>
    </details>
  );
}

// Summary strip, then the results table, then the regulatory notice at the bottom
// (verbatim, ADR 0003). Farmland class acres come directly from SDA; the preliminary
// FPPA/LESA determination follows after this screening step.
export function ScreeningResults({ result }: { result: ScreeningResponse }) {
  const notice = result.display.regulatory_notice;
  const analysis = result.display.analysis;
  const block = result.display.map;
  const farmlandLegend = block?.layers.find((layer) => layer.id === FARMLAND_LAYER_ID)?.legend;
  return (
    <div className="flex flex-col gap-3">
      {analysis && <SummaryStrip analysis={analysis} />}
      {analysis && (
        <div className={RESULT_CARD}>
          <ResultsTable analysis={analysis} legend={farmlandLegend} />
        </div>
      )}
      <RegulatoryNotice notice={notice} />
    </div>
  );
}
