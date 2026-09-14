import { useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { Button, IconButton, Input } from '@/ui';

export interface KeyValueEditorProps {
  value: Record<string, string>;
  onChange: (next: Record<string, string>) => void;
  keyPlaceholder?: string;
  valuePlaceholder?: string;
  addLabel?: string;
  mono?: boolean;
}

/** Editable key/value rows; each change is committed on blur. */
export function KeyValueEditor({ value, onChange, keyPlaceholder = 'key', valuePlaceholder = 'value', addLabel = 'Add', mono }: KeyValueEditorProps) {
  const entries = Object.entries(value);
  const [draft, setDraft] = useState<{ k: string; v: string } | null>(null);

  const rename = (oldKey: string, newKey: string) => {
    const k = newKey.trim();
    if (!k || k === oldKey) return;
    const next: Record<string, string> = {};
    for (const [key, val] of entries) next[key === oldKey ? k : key] = val;
    onChange(next);
  };
  const setVal = (key: string, v: string) => { if (value[key] !== v) onChange({ ...value, [key]: v }); };
  const remove = (key: string) => { const next = { ...value }; delete next[key]; onChange(next); };
  const commitDraft = () => {
    if (!draft) return;
    const k = draft.k.trim();
    if (k) onChange({ ...value, [k]: draft.v });
    setDraft(null);
  };

  return (
    <div className="flex flex-col gap-1">
      {entries.map(([k, v]) => (
        <div key={k} className="grid grid-cols-[1fr_1fr_auto] items-center gap-1">
          <Input defaultValue={k} mono={mono} className="h-7" onBlur={(e) => rename(k, e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
          <Input defaultValue={v} mono={mono} className="h-7" onBlur={(e) => setVal(k, e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }} />
          <IconButton label="Remove" size="icon-xs" onClick={() => remove(k)}><Trash2 /></IconButton>
        </div>
      ))}
      {draft ? (
        <div className="grid grid-cols-[1fr_1fr_auto] items-center gap-1">
          <Input autoFocus placeholder={keyPlaceholder} mono={mono} className="h-7" value={draft.k} onChange={(e) => setDraft({ ...draft, k: e.target.value })} onKeyDown={(e) => { if (e.key === 'Enter') commitDraft(); if (e.key === 'Escape') setDraft(null); }} />
          <Input placeholder={valuePlaceholder} mono={mono} className="h-7" value={draft.v} onChange={(e) => setDraft({ ...draft, v: e.target.value })} onBlur={commitDraft} onKeyDown={(e) => { if (e.key === 'Enter') commitDraft(); if (e.key === 'Escape') setDraft(null); }} />
          <IconButton label="Discard" size="icon-xs" onClick={() => setDraft(null)}><Trash2 /></IconButton>
        </div>
      ) : (
        <Button variant="ghost" size="xs" className="w-fit" onClick={() => setDraft({ k: '', v: '' })}><Plus /> {addLabel}</Button>
      )}
    </div>
  );
}
