import { ChevronLeft, KeyRound, MoreHorizontal, ShieldCheck, Trash2, UserRound, Users } from 'lucide-react';
import type { TopologySummary } from '@/api/client';
import {
  Badge, Button, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger, IconButton,
} from '@/ui';
import { ago } from '@/lib/time';
import { ROLE_LABEL, ROLE_TONE } from '@/lib/roles';
import type { StaffRow } from '@/features/library/model';
import { StatusBadge } from '@/features/library/TopologyCard';
import type { StaffState } from './useStaff';

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

/** The role and account flags next to a name. */
function Tags({ row }: { row: StaffRow }) {
  return (
    <>
      <Badge tone={ROLE_TONE[row.role]}>{ROLE_LABEL[row.role]}</Badge>
      {row.envManaged ? <Badge tone="outline" title="Its password is set by AE3GIS_ADMIN_PASSWORD">environment</Badge> : null}
      {row.mustChangePassword ? <Badge tone="warning" title="Has not replaced the temporary password yet">temporary password</Badge> : null}
    </>
  );
}

/** Reset password, change role, remove. Nothing for yourself or the environment's admin. */
function StaffMenu({ row, staff, meId }: { row: StaffRow; staff: StaffState; meId: string | null | undefined }) {
  if (row.id === meId || row.envManaged) return null;
  const other = row.role === 'admin' ? 'instructor' : 'admin';
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <IconButton label={`Manage ${row.username}`} size="icon-sm" onClick={(e) => e.stopPropagation()}><MoreHorizontal /></IconButton>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" onClick={(e) => e.stopPropagation()}>
        <DropdownMenuItem onSelect={() => staff.resetPassword(row)}><KeyRound /> Reset password</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => staff.setRole(row, other)}>
          {other === 'admin' ? <><ShieldCheck /> Make admin</> : <><UserRound /> Make instructor</>}
        </DropdownMenuItem>
        <DropdownMenuSeparator />
        <DropdownMenuItem variant="danger" onSelect={() => staff.setPending({ kind: 'remove', member: row })}><Trash2 /> Remove…</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** One row per admin or instructor: their class, their topologies, what runs. */
export function StaffTable({ rows, onOpen, staff, meId }: {
  rows: StaffRow[];
  onOpen: (id: string) => void;
  staff: StaffState;
  meId: string | null | undefined;
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full text-xs">
        <thead>
          <tr className="border-b border-border text-left text-2xs uppercase tracking-wide text-fg-subtle">
            <th className="px-3 py-2 font-medium">Name</th>
            <th className="px-3 py-2 font-medium">Students</th>
            <th className="px-3 py-2 font-medium">Topologies</th>
            <th className="px-3 py-2 font-medium">Running</th>
            <th className="px-3 py-2 font-medium">Last seen</th>
            <th className="px-3 py-2"><span className="sr-only">Actions</span></th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map((row) => (
            <tr key={row.id} className="group cursor-pointer hover:bg-hover/40" onClick={() => onOpen(row.id)}>
              <td className="px-3 py-1.5">
                <span className="flex flex-wrap items-center gap-1.5">
                  <button type="button" className="text-[13px] font-medium hover:text-accent" onClick={(e) => { e.stopPropagation(); onOpen(row.id); }}>
                    {row.username}
                  </button>
                  {row.id === meId ? <span className="text-fg-subtle">(you)</span> : null}
                  <Tags row={row} />
                </span>
              </td>
              <td className="tabular px-3 py-1.5 text-fg-muted">
                {row.studentCount}
                {row.signupOpen ? <span className="ml-1.5 text-success" title="Sign-up is open">· open</span> : null}
              </td>
              <td className="tabular px-3 py-1.5 text-fg-muted">{row.topologies.length}</td>
              <td className="max-w-56 px-3 py-1.5"><RunningCell running={row.running} /></td>
              <td className="whitespace-nowrap px-3 py-1.5 text-fg-muted">{ago(row.lastSeen)}</td>
              <td className="px-3 py-1 text-right" onClick={(e) => e.stopPropagation()}><StaffMenu row={row} staff={staff} meId={meId} /></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Over one staff member's topologies: who, their class, their account actions. */
export function StaffHeader({ row, staff, meId, onBack, onStudents }: {
  row: StaffRow;
  staff: StaffState;
  meId: string | null | undefined;
  onBack: () => void;
  onStudents: () => void;
}) {
  const manageable = row.id !== meId && !row.envManaged;
  return (
    <div className="flex flex-wrap items-center gap-3">
      <Button size="sm" variant="ghost" onClick={onBack} className="-ml-2"><ChevronLeft /> Staff</Button>
      <div className="min-w-0">
        <h1 className="flex flex-wrap items-center gap-1.5 text-base font-semibold"><span className="truncate">{row.username}</span> <Tags row={row} /></h1>
        <p className="text-xs text-fg-muted">
          Seen {ago(row.lastSeen)} · {row.topologies.length} topolog{row.topologies.length === 1 ? 'y' : 'ies'}
          {row.running.length ? ` · ${row.running.length} running` : ''}
        </p>
      </div>
      <div className="ml-auto flex items-center gap-1">
        <Button size="sm" variant="ghost" onClick={onStudents}><Users /> {row.studentCount} student{row.studentCount === 1 ? '' : 's'}</Button>
        {manageable ? (
          <>
            <Button size="sm" variant="ghost" onClick={() => staff.resetPassword(row)} loading={staff.busy === `pw:${row.id}`}><KeyRound /> Reset password</Button>
            <Button size="sm" variant="danger-soft" onClick={() => staff.setPending({ kind: 'remove', member: row })}><Trash2 /> Remove</Button>
          </>
        ) : null}
      </div>
    </div>
  );
}
