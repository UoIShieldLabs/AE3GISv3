import { ChevronLeft, KeyRound, Trash2 } from 'lucide-react';
import type { TopologySummary } from '@/api/client';
import { Button, IconButton } from '@/ui';
import { ago } from '@/lib/time';
import { lessonCopy, type StudentRow } from '@/features/library/model';
import { StatusBadge } from '@/features/library/TopologyCard';
import type { ClassState } from './useClass';

function RunningCell({ running }: { running: TopologySummary[] }) {
  if (running.length === 0) return <span className="text-fg-subtle">—</span>;
  const [first, ...rest] = running;
  return (
    <span className="flex min-w-0 items-center gap-2">
      <StatusBadge status={first.status} />
      <span className="min-w-0 truncate" title={first.name}>{first.name}</span>
      {rest.length ? <span className="shrink-0 text-fg-subtle">+{rest.length}</span> : null}
    </span>
  );
}

function StudentActions({ row, cls }: { row: StudentRow; cls: ClassState }) {
  return (
    <div className="flex items-center justify-end gap-0.5" onClick={(e) => e.stopPropagation()}>
      <IconButton label={`Reset ${row.username}'s password`} size="icon-sm" onClick={() => cls.resetPassword(row)} loading={cls.busy === `pw:${row.id}`}><KeyRound /></IconButton>
      <IconButton label={`Remove ${row.username}`} size="icon-sm" className="hover:text-danger" onClick={() => cls.setPending({ kind: 'remove', student: row })}><Trash2 /></IconButton>
    </div>
  );
}

/** One row per student: what they have, what runs, when they were last seen.
 *  Following a lesson adds the state of each student's copy of it. */
export function StudentsTable({ rows, lesson, onOpen, cls }: {
  rows: StudentRow[];
  lesson: TopologySummary | null;
  onOpen: (studentId: string) => void;
  cls: ClassState;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-2xs uppercase tracking-wide text-fg-subtle">
            <th className="px-3 py-2 font-medium">Student</th>
            {lesson ? <th className="px-3 py-2 font-medium">This lesson</th> : null}
            <th className="px-3 py-2 font-medium">Topologies</th>
            <th className="px-3 py-2 font-medium">Running</th>
            <th className="px-3 py-2 font-medium">Last seen</th>
            <th className="px-3 py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => {
            const copy = lesson ? lessonCopy(row, lesson.id) : undefined;
            return (
              <tr key={row.id} className="group cursor-pointer hover:bg-hover/40" onClick={() => onOpen(row.id)}>
                <td className="px-3 py-1.5">
                  <button type="button" className="text-[13px] font-medium hover:text-accent" onClick={(e) => { e.stopPropagation(); onOpen(row.id); }}>
                    {row.username}
                  </button>
                </td>
                {lesson ? (
                  <td className="px-3 py-1.5">{copy ? <StatusBadge status={copy.status} /> : <span className="text-fg-subtle">not started</span>}</td>
                ) : null}
                <td className="tabular px-3 py-1.5 text-fg-muted">{row.topologies.length}</td>
                <td className="max-w-56 px-3 py-1.5"><RunningCell running={row.running} /></td>
                <td className="whitespace-nowrap px-3 py-1.5 text-fg-muted">{ago(row.lastSeen)}</td>
                <td className="px-3 py-1"><StudentActions row={row} cls={cls} /></td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

/** Over one student's topologies: who, when, and their account actions. */
export function StudentHeader({ row, cls, onBack }: { row: StudentRow; cls: ClassState; onBack: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button size="sm" variant="ghost" onClick={onBack} className="-ml-2"><ChevronLeft /> Students</Button>
      <div className="min-w-0">
        <h1 className="truncate text-base font-semibold">{row.username}</h1>
        <p className="text-xs text-fg-muted">
          Seen {ago(row.lastSeen)} · {row.topologies.length} topolog{row.topologies.length === 1 ? 'y' : 'ies'}
          {row.running.length ? ` · ${row.running.length} running` : ''}
        </p>
      </div>
      <div className="ml-auto flex items-center gap-1">
        <Button size="sm" variant="ghost" onClick={() => cls.resetPassword(row)} loading={cls.busy === `pw:${row.id}`}><KeyRound /> Reset password</Button>
        <Button size="sm" variant="danger-soft" onClick={() => cls.setPending({ kind: 'remove', student: row })}><Trash2 /> Remove</Button>
      </div>
    </div>
  );
}
