import { Button, Dialog } from '@/ui';
import type { ClassState } from './useClass';

/** Confirm removing a student; show a reset password once. */
export function ClassDialogs({ cls }: { cls: ClassState }) {
  const { pending, setPending } = cls;
  return (
    <>
      <Dialog
        open={pending?.kind === 'remove'}
        onOpenChange={(o) => !o && setPending(null)}
        title="Remove this student?"
        description={pending?.kind === 'remove' ? pending.student.username : undefined}
        size="sm"
        footer={pending?.kind === 'remove' ? (
          <>
            <Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => cls.remove(pending.student)}>Remove</Button>
          </>
        ) : null}
      >
        <p className="text-xs text-fg-muted">Their account and all their topologies are deleted. Destroy their running labs first.</p>
      </Dialog>

      <Dialog
        open={pending?.kind === 'password'}
        onOpenChange={(o) => !o && setPending(null)}
        title="Temporary password"
        description={pending?.kind === 'password' ? `For ${pending.student}: they were signed out everywhere.` : undefined}
        size="sm"
        footer={<Button variant="primary" onClick={() => setPending(null)}>Done</Button>}
      >
        {pending?.kind === 'password' ? (
          <div className="flex flex-col gap-2">
            <code className="rounded-md bg-surface-2 px-3 py-2 text-center font-mono text-base tracking-widest">{pending.password}</code>
            <p className="text-xs text-fg-muted">Shown once. They sign in with it and can change it from their user menu.</p>
          </div>
        ) : null}
      </Dialog>
    </>
  );
}
