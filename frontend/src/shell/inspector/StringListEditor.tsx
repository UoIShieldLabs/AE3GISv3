import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { IconButton, Input } from '@/ui';

export interface StringListEditorProps {
  value: string[];
  onChange: (next: string[]) => void;
  placeholder?: string;
  /** Normalise + validate; return `{ value }` or `{ error }`. */
  parse?: (raw: string) => { value: string } | { error: string };
  mono?: boolean;
}

export function StringListEditor({ value, onChange, placeholder, parse, mono }: StringListEditorProps) {
  const [draft, setDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const add = () => {
    const raw = draft.trim();
    if (!raw) return;
    const parsed = parse ? parse(raw) : { value: raw };
    if ('error' in parsed) { setError(parsed.error); return; }
    if (value.includes(parsed.value)) { setError('Already added'); return; }
    onChange([...value, parsed.value]);
    setDraft('');
    setError(null);
  };
  return (
    <div className="flex flex-col gap-1">
      {value.map((v) => (
        <div key={v} className="flex items-center gap-1 rounded-md bg-surface-2 px-2 py-1 text-xs">
          <span className={mono ? 'min-w-0 flex-1 truncate font-mono' : 'min-w-0 flex-1 truncate'}>{v}</span>
          <IconButton label="Remove" size="icon-xs" onClick={() => onChange(value.filter((x) => x !== v))}><Trash2 /></IconButton>
        </div>
      ))}
      <div className="flex items-center gap-1">
        <Input
          value={draft}
          mono={mono}
          placeholder={placeholder}
          className="h-7"
          aria-invalid={error ? true : undefined}
          onChange={(e) => { setDraft(e.target.value); setError(null); }}
          onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); add(); } }}
        />
        <IconButton label="Add" size="icon-sm" variant="secondary" onClick={add} disabled={!draft.trim()}><Plus /></IconButton>
      </div>
      {error ? <span className="text-2xs text-danger">{error}</span> : null}
    </div>
  );
}
