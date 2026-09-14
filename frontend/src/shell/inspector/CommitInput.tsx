import { useState } from 'react';
import { Input, type InputProps } from '@/ui';

export interface CommitInputProps extends Omit<InputProps, 'value' | 'onChange'> {
  value: string;
  onCommit: (value: string) => void;
  /** Return an error message to block the commit. */
  validate?: (value: string) => string | null;
}

/** Text input that writes to the store on blur/Enter (so undo gets one step per edit, not per keystroke). */
export function CommitInput({ value, onCommit, validate, ...props }: CommitInputProps) {
  const [draft, setDraft] = useState(value);
  const [prev, setPrev] = useState(value);
  const [error, setError] = useState<string | null>(null);
  if (prev !== value) {
    setPrev(value);
    setDraft(value);
    setError(null);
  }
  const commit = () => {
    const v = draft.trim();
    if (v === value) { setError(null); return; }
    const err = validate?.(v) ?? null;
    setError(err);
    if (!err) onCommit(v);
  };
  return (
    <div className="flex flex-col gap-1">
      <Input
        {...props}
        value={draft}
        aria-invalid={error ? true : props['aria-invalid']}
        onChange={(e) => { setDraft(e.target.value); if (error) setError(validate?.(e.target.value.trim()) ?? null); }}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { e.preventDefault(); (e.target as HTMLInputElement).blur(); }
          if (e.key === 'Escape') { setDraft(value); setError(null); (e.target as HTMLInputElement).blur(); }
        }}
      />
      {error ? <span className="text-2xs text-danger">{error}</span> : null}
    </div>
  );
}
