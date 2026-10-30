import { useId, useState } from 'react';
import type { ChangeEvent } from 'react';
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
  const fileId = useId();
  const messageId = useId();
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
    <div className="flex flex-col gap-2">
      <label htmlFor={textId} className="font-medium text-sm">
        Paste GeoJSON (Polygon or MultiPolygon)
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
      <div className="flex flex-wrap items-center gap-2">
        <Button
          type="button"
          size="sm"
          variant="secondary"
          onClick={() => apply(text)}
          disabled={!text.trim()}
        >
          Use pasted AOI
        </Button>
        <label htmlFor={fileId} className="text-sm">
          or upload
        </label>
        <input
          id={fileId}
          type="file"
          accept=".geojson,.json,application/geo+json,application/json"
          onChange={onFile}
          className="max-w-[14rem] text-xs"
        />
      </div>
      {message && (
        <p id={messageId} role="alert" className="text-destructive text-sm">
          {message}
        </p>
      )}
    </div>
  );
}
