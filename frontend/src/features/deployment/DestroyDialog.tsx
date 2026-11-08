import { useAppStore } from '@/store';
import { Button, Dialog } from '@/ui';
import { destroyTopology } from './actions';

/** Before destroying a lab: save it to resume later, or destroy it outright. Closing keeps it running. */
export function DestroyDialog() {
  const open = useAppStore((s) => s.destroyDialogOpen);
  const close = () => useAppStore.getState().setDestroyDialogOpen(false);
  const destroy = (save: boolean) => { close(); void destroyTopology({ save }); };

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => { if (!o) close(); }}
      title="Save before destroying?"
      size="sm"
      footer={
        <>
          <Button variant="danger-soft" onClick={() => destroy(false)}>Don&apos;t save</Button>
          <Button variant="primary" onClick={() => destroy(true)} autoFocus>Save &amp; destroy</Button>
        </>
      }
    >
      <p className="text-sm text-fg-muted">Save the lab so you can resume it later.</p>
    </Dialog>
  );
}
