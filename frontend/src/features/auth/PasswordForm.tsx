import { useState } from 'react';
import * as api from '@/api/client';
import { Button, Field, Input } from '@/ui';

const MIN_PASSWORD = 8;

/** Current + new password, changed through the API. Used by the user menu's
 *  dialog and by the screen that asks for a new password after a temporary one. */
export function PasswordForm({ currentLabel = 'Current password', submitLabel = 'Change password', onDone, onCancel }: {
  currentLabel?: string;
  submitLabel?: string;
  onDone: () => void | Promise<void>;
  onCancel?: () => void;
}) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < MIN_PASSWORD) { setError(`The new password needs at least ${MIN_PASSWORD} characters`); return; }
    setBusy(true);
    setError(null);
    try {
      await api.changePassword(current, next);
      setCurrent('');
      setNext('');
      await onDone();
    } catch (err) {
      setError(api.errorMessage(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
      <Field label={currentLabel}>
        {(ctl) => <Input {...ctl} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} autoFocus />}
      </Field>
      <Field label="New password" hint={`At least ${MIN_PASSWORD} characters`}>
        {(ctl) => <Input {...ctl} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}
      </Field>
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <div className="flex justify-end gap-2 pt-1">
        {onCancel ? <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button> : null}
        <Button type="submit" variant="primary" loading={busy}>{submitLabel}</Button>
      </div>
    </form>
  );
}
