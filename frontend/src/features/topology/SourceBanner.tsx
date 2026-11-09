import { useState } from 'react';
import { RotateCcw, UserRound } from 'lucide-react';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { useIsStudent } from '@/lib/permissions';
import { resetToSource } from '@/features/deployment/actions';
import { Badge, Button, Dialog, Tooltip } from '@/ui';

/** A student's copy whose lesson changed since: one line, with the reset. */
export function SourceBanner() {
  const { sourceId, updateAvailable, deployStatus, busy } = useAppShallow((s) => ({
    sourceId: s.sourceId, updateAvailable: s.updateAvailable, deployStatus: s.deployStatus, busy: s.busy,
  }));
  const isStudent = useIsStudent();
  const [confirm, setConfirm] = useState(false);
  if (!isStudent || !sourceId || !updateAvailable) return null;

  const labUp = deployStatus !== 'idle' && deployStatus !== 'error';
  return (
    <div className="flex items-center gap-2 border-b border-border bg-info-soft px-3 py-1 text-xs text-info" role="status">
      <span className="min-w-0 flex-1 truncate">Your instructor updated this lesson.</span>
      <Button size="xs" variant="ghost" disabled={labUp || busy} title={labUp ? 'Destroy the lab first' : undefined} onClick={() => setConfirm(true)}>
        <RotateCcw /> Reset to latest
      </Button>
      <Dialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Reset to the latest version?"
        description="Your changes to this copy and its saved lab state are discarded."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirm(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => { setConfirm(false); void resetToSource(); }}>Reset</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">Tutorials and scenarios update too.</p>
      </Dialog>
    </div>
  );
}

/** Next to the topology's name, for the instructor in classroom mode: whose
 *  topology this is (a student's) and whether students see it. Quiet chips
 *  with the detail in a tooltip, rather than a banner. */
export function RecordChips() {
  const { owner, published } = useAppShallow((s) => ({ owner: s.owner, published: s.published }));
  const accounts = useAppStore((s) => !!s.authRequired);
  const isStudent = useIsStudent();
  if (!accounts || isStudent) return null;
  return (
    <>
      {owner ? (
        <Tooltip content={`${owner.username}'s topology: saving changes theirs`}>
          <Badge tone="outline" className="max-w-32 shrink-0"><UserRound className="size-3 shrink-0" /><span className="truncate">{owner.username}</span></Badge>
        </Tooltip>
      ) : null}
      {published ? (
        <Tooltip content="Published: students open their own copy and are offered what you save">
          <Badge tone="accent" className="shrink-0">Published</Badge>
        </Tooltip>
      ) : null}
    </>
  );
}
