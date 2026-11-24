import { Button, Dialog } from '@/ui';
import { TemporaryPasswordDialog } from './TemporaryPasswordDialog';
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

      <TemporaryPasswordDialog
        open={pending?.kind === 'password'}
        who={pending?.kind === 'password' ? `${pending.student}: they were signed out everywhere` : undefined}
        password={pending?.kind === 'password' ? pending.password : undefined}
        onClose={() => setPending(null)}
      />
    </>
  );
}
