import { useCallback, useEffect, useState } from 'react';
import { Copy, KeyRound, RefreshCw, RotateCcw, Square, Trash2, Users } from 'lucide-react';
import * as api from '@/api/client';
import { Badge, Button, Dialog, IconButton, Sheet, Spinner, Switch, toast } from '@/ui';

export interface ClassSheetProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** After a lab was destroyed or a student removed (the library refreshes). */
  onChanged?: () => void;
}

const STATUS_TONE: Record<string, 'success' | 'neutral' | 'warning' | 'danger'> = {
  deployed: 'success', idle: 'neutral', deploying: 'warning', destroying: 'warning', error: 'danger',
};
// Lab statuses change while the sheet is open (students deploy, destroys finish).
const POLL_MS = 5000;

function ago(iso: string | null | undefined): string {
  if (!iso) return 'never';
  const s = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

type Pending =
  | { kind: 'destroy'; lab: api.Student['labs'][number]; student: string }
  | { kind: 'remove'; student: api.Student }
  | { kind: 'password'; student: string; password: string };

/** The instructor's class: sign-up with the join code, and every student with
 *  their running labs (on this host), password resets and removal. */
export function ClassSheet({ open, onOpenChange, onChanged }: ClassSheetProps) {
  const [settings, setSettings] = useState<api.ClassSettings | null>(null);
  const [students, setStudents] = useState<api.Students | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([api.getClassSettings(), api.listStudents()]);
      setSettings(c);
      setStudents(s);
    } catch (err) {
      toast.error('Could not load the class', { description: api.errorMessage(err) });
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    void refresh();
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [open, refresh]);

  const run = async (key: string, fn: () => Promise<void>, failure: string) => {
    setBusy(key);
    try {
      await fn();
    } catch (err) {
      toast.error(failure, { description: api.errorMessage(err) });
    } finally {
      setBusy(null);
    }
  };

  const setSignup = (signup_open: boolean) =>
    void run('signup', async () => setSettings(await api.updateClassSettings({ signup_open })), 'Could not change sign-up');
  const rotate = () =>
    void run('rotate', async () => setSettings(await api.updateClassSettings({ rotate_join_code: true })), 'Could not make a new code');
  const copyCode = async () => {
    if (!settings?.join_code) return;
    try {
      await navigator.clipboard.writeText(settings.join_code);
      toast.success('Join code copied');
    } catch {
      toast.info(settings.join_code);
    }
  };

  const destroy = (lab: { id: string }, save: boolean) =>
    void run(`lab:${lab.id}`, async () => {
      setPending(null);
      await api.destroyTopology(lab.id, { save });
      toast.success(save ? 'Saving and destroying the lab' : 'Destroying the lab');
      await refresh();
      onChanged?.();
    }, 'Could not destroy the lab');
  const resetPassword = (student: api.Student) =>
    void run(`pw:${student.id}`, async () => {
      const { password } = await api.resetStudentPassword(student.id);
      setPending({ kind: 'password', student: student.username, password });
    }, 'Could not reset the password');
  const remove = (student: api.Student) =>
    void run(`rm:${student.id}`, async () => {
      setPending(null);
      await api.removeStudent(student.id);
      toast.success(`Removed ${student.username}`);
      await refresh();
      onChanged?.();
    }, 'Could not remove the student');

  const joinUrl = `${window.location.origin}/login`;
  const list = students?.students ?? [];
  const running = list.reduce((n, s) => n + s.labs.length, 0);

  return (
    <Sheet
      open={open}
      onOpenChange={onOpenChange}
      title="Class"
      description="Sign-up, students and their labs"
      size="620px"
      headerAction={<IconButton label="Refresh" size="icon-sm" onClick={() => void refresh()}><RefreshCw /></IconButton>}
    >
      {settings === null || students === null ? (
        <div className="flex justify-center py-10"><Spinner /></div>
      ) : (
        <div className="flex flex-col gap-6 text-xs">
          <section className="flex flex-col gap-3 rounded-lg border border-border p-3">
            <label className="flex items-center justify-between gap-3">
              <span>
                <span className="block text-[13px] font-medium">Students can sign up</span>
                <span className="text-fg-muted">Accounts stay when you turn it off.</span>
              </span>
              <Switch checked={settings.signup_open} disabled={busy === 'signup'} onCheckedChange={setSignup} aria-label="Students can sign up" />
            </label>
            {settings.join_code ? (
              <div className="flex flex-wrap items-center gap-2">
                <code className="rounded-md bg-surface-2 px-3 py-1.5 font-mono text-base tracking-widest">{settings.join_code}</code>
                <IconButton label="Copy join code" size="icon-sm" onClick={() => void copyCode()}><Copy /></IconButton>
                <Button size="xs" variant="ghost" onClick={rotate} loading={busy === 'rotate'}><RotateCcw /> New code</Button>
                <span className="w-full text-fg-muted">
                  Join at <span className="font-mono">{joinUrl}</span>
                  {settings.signup_open ? null : ' (closed now)'}
                </span>
              </div>
            ) : (
              <p className="text-fg-muted">Turn it on to get a join code.</p>
            )}
          </section>

          <section className="flex flex-col gap-2">
            <h3 className="flex items-center gap-2 text-2xs font-semibold uppercase tracking-wide text-fg-muted">
              <Users className="size-3.5" /> Students ({list.length})
              <span className="ml-auto font-normal normal-case tracking-normal text-fg-subtle">
                {running} running · {students.max_labs > 0 ? `max ${students.max_labs} each` : 'no limit'}
              </span>
            </h3>
            {list.length === 0 ? (
              <p className="text-fg-subtle">No students yet.</p>
            ) : (
              <ul className="divide-y divide-border rounded-lg border border-border">
                {list.map((s) => (
                  <li key={s.id} className="flex flex-col gap-2 p-3">
                    <div className="flex items-center gap-2">
                      <span className="min-w-0 flex-1 truncate text-[13px] font-medium">{s.username}</span>
                      <span className="text-fg-subtle">seen {ago(s.last_seen_at)} · {s.topology_count} topolog{s.topology_count === 1 ? 'y' : 'ies'}</span>
                      <IconButton label="Reset password" size="icon-sm" onClick={() => resetPassword(s)} loading={busy === `pw:${s.id}`}><KeyRound /></IconButton>
                      <IconButton label="Remove student" size="icon-sm" className="hover:text-danger" onClick={() => setPending({ kind: 'remove', student: s })}><Trash2 /></IconButton>
                    </div>
                    {s.labs.map((lab) => (
                      <div key={lab.id} className="flex items-center gap-2 rounded-md bg-surface-2/60 px-2 py-1">
                        <Badge tone={STATUS_TONE[lab.status] ?? 'neutral'} dot={lab.status === 'deployed' ? 'pulse' : true}>{lab.status}</Badge>
                        <span className="min-w-0 flex-1 truncate">{lab.name}</span>
                        <Button size="xs" variant="danger-soft" disabled={lab.status === 'destroying' || busy !== null} loading={busy === `lab:${lab.id}`}
                          onClick={() => setPending({ kind: 'destroy', lab, student: s.username })}>
                          <Square /> Destroy
                        </Button>
                      </div>
                    ))}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>
      )}

      <Dialog
        open={pending?.kind === 'destroy'}
        onOpenChange={(o) => !o && setPending(null)}
        title="Destroy this lab?"
        description={pending?.kind === 'destroy' ? `${pending.student}'s “${pending.lab.name}”` : undefined}
        size="sm"
        footer={pending?.kind === 'destroy' ? (
          <>
            <Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
            <Button variant="secondary" onClick={() => destroy(pending.lab, true)}>Save &amp; destroy</Button>
            <Button variant="danger" onClick={() => destroy(pending.lab, false)}>Destroy</Button>
          </>
        ) : null}
      >
        <p className="text-xs text-fg-muted">Save &amp; destroy keeps the student's lab state so their next deploy resumes it.</p>
      </Dialog>

      <Dialog
        open={pending?.kind === 'remove'}
        onOpenChange={(o) => !o && setPending(null)}
        title="Remove this student?"
        description={pending?.kind === 'remove' ? pending.student.username : undefined}
        size="sm"
        footer={pending?.kind === 'remove' ? (
          <>
            <Button variant="ghost" onClick={() => setPending(null)}>Cancel</Button>
            <Button variant="danger" onClick={() => remove(pending.student)}>Remove</Button>
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
    </Sheet>
  );
}
