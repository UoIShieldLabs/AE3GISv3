import { useState } from 'react';
import { GraduationCap, RotateCcw, Send, UserRound } from 'lucide-react';
import { useAppShallow } from '@/store/selectors';
import { useIsStudent } from '@/lib/permissions';
import { resetToSource } from '@/features/deployment/actions';
import { Button, Dialog } from '@/ui';

/** Classroom-mode context over the canvas: a student's copy whose instructor
 *  version changed (reset to it), or, for the instructor, whose topology this
 *  is (a student's) and whether students see it (published). */
export function SourceBanner() {
  const { owner, published, sourceId, updateAvailable, deployStatus, busy } = useAppShallow((s) => ({
    owner: s.owner, published: s.published, sourceId: s.sourceId, updateAvailable: s.updateAvailable,
    deployStatus: s.deployStatus, busy: s.busy,
  }));
  const isStudent = useIsStudent();
  const [confirm, setConfirm] = useState(false);

  if (isStudent && sourceId && updateAvailable) {
    const labUp = deployStatus !== 'idle' && deployStatus !== 'error';
    return (
      <div className="flex items-center gap-2 border-b border-border bg-info-soft px-3 py-1.5 text-xs text-info" role="status">
        <GraduationCap className="size-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate">Your instructor updated this lab since you started it.</span>
        <Button size="xs" variant="ghost" disabled={labUp || busy} title={labUp ? 'Destroy the lab first' : undefined} onClick={() => setConfirm(true)}>
          <RotateCcw /> Reset to latest
        </Button>
        <Dialog
          open={confirm}
          onOpenChange={setConfirm}
          title="Reset to your instructor's latest version?"
          description="Your changes to this copy are replaced, and its saved lab state is discarded."
          size="sm"
          footer={
            <>
              <Button variant="ghost" onClick={() => setConfirm(false)}>Cancel</Button>
              <Button variant="danger" onClick={() => { setConfirm(false); void resetToSource(); }}>Reset</Button>
            </>
          }
        >
          <p className="text-xs text-fg-muted">The tutorials and scenarios update too.</p>
        </Dialog>
      </div>
    );
  }
  if (!isStudent && owner) {
    return (
      <div className="flex items-center gap-2 border-b border-border bg-surface-2 px-3 py-1.5 text-xs text-fg-muted" role="status">
        <UserRound className="size-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate"><span className="font-medium text-fg">{owner.username}</span>'s topology: what you save here is saved to theirs.</span>
      </div>
    );
  }
  if (!isStudent && published) {
    return (
      <div className="flex items-center gap-2 border-b border-border bg-accent-soft px-3 py-1.5 text-xs text-accent" role="status">
        <Send className="size-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate">Published: students work on their own copies, and are offered your saved changes.</span>
      </div>
    );
  }
  return null;
}
