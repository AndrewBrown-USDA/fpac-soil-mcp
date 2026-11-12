import { useId, useRef, useState } from 'react';
import type { ChangeEvent } from 'react';
import { Upload } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { parseAoiText } from './geojson';
import type { PolygonGeometry } from './geojson';

const MAX_FILE_BYTES = 256 * 1024;

// Keyboard path for entering an AOI: paste GeoJSON or pick a .geojson/.json file.
export function GeoJsonInput({
  onGeometry,
}: {
  onGeometry: (geometry: PolygonGeometry) => void;
}) {
  const textId = useId();
  const messageId = useId();
  const headingId = useId();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [text, setText] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const apply = (value: string) => {
    const parsed = parseAoiText(value);
    if (parsed.ok) {
      setMessage(null);
      onGeometry(parsed.geometry);
    } else {
      setMessage(parsed.message);
    }
  };

  const onFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (file.size > MAX_FILE_BYTES) {
      setMessage('The file is larger than 256 KB.');
      return;
    }
    const content = await file.text();
    setText(content);
    apply(content);
  };

  return (
    <div role="group" aria-labelledby={headingId} className="flex flex-col gap-2">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span
          id={headingId}
          className="font-medium text-muted-foreground text-xs uppercase tracking-wide"
        >
          Import AOI
        </span>
        <Button
          type="button"
          variant="primary"
          onClick={() => fileInputRef.current?.click()}
          className="gap-1.5"
        >
          <Upload aria-hidden="true" />
          Upload AOI file
        </Button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".geojson,.json,application/geo+json,application/json"
          onChange={onFile}
          aria-hidden="true"
          tabIndex={-1}
          className="sr-only"
        />
      </div>
      <details>
        <summary className="w-fit cursor-pointer font-medium text-primary text-sm hover:underline">
          Paste GeoJSON instead
        </summary>
        <div className="mt-2 flex flex-col gap-2">
          <label htmlFor={textId} className="font-medium text-sm">
            GeoJSON Polygon or MultiPolygon
          </label>
          <textarea
            id={textId}
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={3}
            spellCheck={false}
            aria-describedby={message ? messageId : undefined}
            className="w-full rounded-md border border-border bg-background p-2 font-mono text-xs"
          />
          <Button
            type="button"
            size="sm"
            variant="secondary"
            onClick={() => apply(text)}
            disabled={!text.trim()}
            className="w-fit"
          >
            Use pasted AOI
          </Button>
        </div>
      </details>
      {message && (
        <p id={messageId} role="alert" className="text-destructive text-sm">
          {message}
        </p>
      )}
    </div>
  );
}
