import type { CSSProperties } from 'react';
import type { FarmlandClass } from './farmlandClasses';
import { AUTHORITY_LABELS, drawOrder } from './mapLayers';
import type { MapBlock, MapLayer, MapLegendItem } from './mapLayers';

export function swatchStyle(farmlandClass: FarmlandClass): CSSProperties {
  if (farmlandClass.pattern === 'hatched') {
    return {
      backgroundColor: farmlandClass.color,
      backgroundImage:
        'repeating-linear-gradient(45deg, rgba(0, 0, 0, 0.35) 0 2px, transparent 2px 6px)',
    };
  }
  return { backgroundColor: farmlandClass.color };
}

export function Swatch({ farmlandClass }: { farmlandClass: FarmlandClass }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-4 shrink-0 rounded-sm border border-border"
      style={swatchStyle(farmlandClass)}
    />
  );
}

const HATCH = 'rgba(0, 0, 0, 0.35) 0 2px, transparent 2px 6px';

// CSS stand-in for each server legend pattern (strategy section 5).
export function legendSwatchStyle(item: MapLegendItem): CSSProperties {
  switch (item.pattern) {
    case 'diagonal_hatch':
      return {
        backgroundColor: item.color,
        backgroundImage: `repeating-linear-gradient(45deg, ${HATCH})`,
      };
    case 'cross_hatch':
      return {
        backgroundColor: item.color,
        backgroundImage: `repeating-linear-gradient(45deg, ${HATCH}), repeating-linear-gradient(-45deg, ${HATCH})`,
      };
    case 'dot_stipple':
      return {
        backgroundColor: item.color,
        backgroundImage: 'radial-gradient(rgba(0, 0, 0, 0.5) 1px, transparent 1.5px)',
        backgroundSize: '4px 4px',
      };
    case 'outline':
      return { backgroundColor: 'transparent', border: `2px solid ${item.color}` };
    case 'dashed_outline':
      return { backgroundColor: 'transparent', border: `2px dashed ${item.color}` };
    default:
      return { backgroundColor: item.color };
  }
}

export function LegendSwatch({ item }: { item: MapLegendItem }) {
  return (
    <span
      aria-hidden="true"
      className="inline-block h-3 w-4 shrink-0 rounded-sm border border-border"
      style={legendSwatchStyle(item)}
    />
  );
}

function legendItemDescription(item: MapLegendItem): string {
  const pattern = item.pattern?.replaceAll('_', ' ');
  return [item.code ? `Code ${item.code}` : null, pattern ? `${pattern} symbol` : 'solid symbol']
    .filter(Boolean)
    .join(', ');
}

function layerNotes(layer: MapLayer): string[] {
  const notes: string[] = [];
  if (layer.delivery !== 'inline_geojson' || !layer.feature_collection) {
    notes.push('Not loaded');
  }
  if (layer.simplified) {
    const tolerance = layer.simplify_tolerance_m;
    notes.push(
      tolerance != null
        ? `Simplified for display (about ${tolerance} m); acreage uses exact shapes`
        : 'Simplified for display; acreage uses exact shapes',
    );
  }
  if (layer.truncated) notes.push('Partial layer: features dropped by the size limit');
  if (layer.id === 'corridor_direct' && layer.delivery === 'inline_geojson') {
    // A right-of-way strip can be a few pixels wide when the whole corridor is in view.
    notes.push('Narrow corridor: zoom in along the line to see the farmland classes');
  }
  return notes;
}

// Server legends, one block per layer, in the order drawn (top layer first); text
// codes keep meaning off colour alone. Warnings from the server follow the layers.
export function MapLegend({ block }: { block: MapBlock }) {
  const layers = drawOrder(block.layers).reverse();
  if (layers.length === 0) return null;
  return (
    <div>
      <h3 className="font-medium text-sm">Map layers</h3>
      <p className="mt-1 text-muted-foreground text-xs">
        Screening result layers are shown here. Context overlays such as imagery provide geographic
        reference only; they are not screening evidence.
      </p>
      <ul className="mt-1 grid gap-2 text-sm">
        {layers.map((layer) => {
          const notes = layerNotes(layer);
          return (
            <li key={layer.id} className="flex flex-col gap-1">
              <span className="font-medium">{layer.title}</span>
              <span className="text-muted-foreground text-xs">
                {AUTHORITY_LABELS[layer.authority] ?? layer.authority}. Source:{' '}
                {layer.source}
                {layer.data_vintage ? ` (${layer.data_vintage})` : ''}
              </span>
              {notes.map((note) => (
                <span key={note} className="text-muted-foreground text-xs italic">
                  {note}
                </span>
              ))}
              {(layer.legend ?? []).length > 0 && (
                <ul className="grid gap-1">
                  {(layer.legend ?? []).map((item) => (
                    <li
                      key={item.value}
                      aria-label={`${item.label}${item.code ? `, code ${item.code}` : ''}; ${legendItemDescription(item)}`}
                      className="flex items-center gap-2"
                    >
                      <LegendSwatch item={item} />
                      {item.code && (
                        <span className="font-mono text-xs">[{item.code}]</span>
                      )}
                      <span>{item.label}</span>
                    </li>
                  ))}
                </ul>
              )}
            </li>
          );
        })}
      </ul>
      {(block.warnings ?? []).length > 0 && (
        <ul className="mt-2 grid gap-1 text-amber-700 text-xs dark:text-amber-400">
          {(block.warnings ?? []).map((warning) => (
            <li key={warning}>{warning}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
