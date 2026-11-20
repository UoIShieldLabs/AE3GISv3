import { Button, Dialog } from '@/ui';

/** A temporary password, shown once: for a reset, or a new staff account. */
export function TemporaryPasswordDialog({ open, title = 'Temporary password', who, password, onClose }: {
  open: boolean;
  title?: string;
  /** The account's username. */
  who: string | undefined;
  password: string | undefined;
  onClose: () => void;
}) {
  return (
    <Dialog
      open={open}
      onOpenChange={(o) => !o && onClose()}
      title={title}
      description={who ? `For ${who}.` : undefined}
      size="sm"
      footer={<Button variant="primary" onClick={onClose}>Done</Button>}
    >
      {password ? (
        <div className="flex flex-col gap-2">
          <code className="rounded-md bg-surface-2 px-3 py-2 text-center font-mono text-base tracking-widest">{password}</code>
          <p className="text-xs text-fg-muted">Shown once. They sign in with it and then choose a password of their own.</p>
        </div>
      ) : null}
    </Dialog>
  );
}
