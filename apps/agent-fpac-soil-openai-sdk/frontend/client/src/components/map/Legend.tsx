import type { CSSProperties } from 'react';
import { FARMLAND_CLASSES } from './farmlandClasses';
import type { FarmlandClass, FarmlandClassKey } from './farmlandClasses';

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

// Colour swatch, text code and label for every class present in the result.
export function Legend({ present }: { present: ReadonlySet<FarmlandClassKey> }) {
  const shown = FARMLAND_CLASSES.filter((farmlandClass) =>
    present.has(farmlandClass.key),
  );
  if (shown.length === 0) return null;
  return (
    <div>
      <h3 className="font-medium text-sm">Legend</h3>
      <ul className="mt-1 grid gap-1 text-sm">
        {shown.map((farmlandClass) => (
          <li key={farmlandClass.key} className="flex items-center gap-2">
            <Swatch farmlandClass={farmlandClass} />
            <span className="font-mono text-xs">[{farmlandClass.code}]</span>
            <span>{farmlandClass.label}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
