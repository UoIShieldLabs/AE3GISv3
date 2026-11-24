import { useState } from 'react';
import * as api from '@/api/client';
import { Button, Dialog, Field, Input, Select } from '@/ui';
import { TemporaryPasswordDialog } from '@/features/class/TemporaryPasswordDialog';
import type { StaffRow } from '@/features/library/model';
import type { StaffRef, StaffState } from './useStaff';

const ROLE_OPTIONS: { value: api.StaffRole; label: string }[] = [
  { value: 'instructor', label: 'Instructor: their own topologies and class' },
  { value: 'admin', label: 'Admin: everything, this host and the staff too' },
];

function AddStaffForm({ staff }: { staff: StaffState }) {
  const [username, setUsername] = useState('');
  const [role, setRole] = useState<api.StaffRole>('instructor');
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await staff.add(username.trim(), role);
    } catch (err) {
      setError(api.errorMessage(err));
    }
  };
  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
      <Field label="Username" hint="3–32 characters: letters, digits, “.”, “_” or “-”">
        {(ctl) => <Input {...ctl} value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="off" autoFocus />}
      </Field>
      <Field label="Role">
        {(ctl) => <Select id={ctl.id} value={role} onValueChange={setRole} options={ROLE_OPTIONS} />}
      </Field>
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <div className="flex justify-end gap-2 pt-1">
        <Button type="button" variant="ghost" onClick={() => staff.setPending(null)}>Cancel</Button>
        <Button type="submit" variant="primary" loading={staff.busy === 'add'} disabled={!username.trim()}>Add</Button>
      </div>
    </form>
  );
}

function AddStaffDialog({ staff }: { staff: StaffState }) {
  const open = staff.pending?.kind === 'add';
  return (
    <Dialog open={open} onOpenChange={(o) => !o && staff.setPending(null)} title="Add staff" description="They get a temporary password to sign in with, then choose their own." size="sm">
      {/* Mounted per opening, so each starts empty. */}
      {open ? <AddStaffForm staff={staff} /> : null}
    </Dialog>
  );
}

function RemoveStaffForm({ staff, member, rows, meId }: {
  staff: StaffState;
  member: StaffRef;
  rows: StaffRow[];
  meId: string | null | undefined;
}) {
  const heirs = rows.filter((r) => r.id !== member.id);
  const [heirId, setHeirId] = useState<string | undefined>(() => (heirs.some((r) => r.id === meId) ? meId ?? undefined : heirs[0]?.id));
  const heir = heirs.find((r) => r.id === heirId);
  const row = rows.find((r) => r.id === member.id);
  return (
    <div className="flex flex-col gap-3 text-xs">
      <Field label="Hand their work to" hint={row ? `${row.topologies.length} topolog${row.topologies.length === 1 ? 'y' : 'ies'} (running labs keep running) and ${row.studentCount} student${row.studentCount === 1 ? '' : 's'}.` : undefined}>
        {(ctl) => (
          <Select
            id={ctl.id}
            value={heirId}
            onValueChange={setHeirId}
            options={heirs.map((r) => ({ value: r.id, label: r.id === meId ? `${r.username} (you)` : r.username }))}
          />
        )}
      </Field>
      <div className="flex justify-end gap-2 pt-1">
        <Button variant="ghost" onClick={() => staff.setPending(null)}>Cancel</Button>
        <Button
          variant="danger"
          disabled={!heir}
          loading={staff.busy === `rm:${member.id}`}
          onClick={() => heir && void staff.remove(member, heir)}
        >
          Remove
        </Button>
      </div>
    </div>
  );
}

function RemoveStaffDialog({ staff, rows, meId }: { staff: StaffState; rows: StaffRow[]; meId: string | null | undefined }) {
  const pending = staff.pending?.kind === 'remove' ? staff.pending : null;
  return (
    <Dialog
      open={!!pending}
      onOpenChange={(o) => !o && staff.setPending(null)}
      title={`Remove ${pending?.member.username ?? ''}?`}
      description="Their account goes; nothing they made is destroyed."
      size="sm"
    >
      {pending ? <RemoveStaffForm key={pending.member.id} staff={staff} member={pending.member} rows={rows} meId={meId} /> : null}
    </Dialog>
  );
}

/** Add, remove, and the temporary password shown once. */
export function StaffDialogs({ staff, rows, meId }: { staff: StaffState; rows: StaffRow[]; meId: string | null | undefined }) {
  const pw = staff.pending?.kind === 'password' ? staff.pending : null;
  return (
    <>
      <AddStaffDialog staff={staff} />
      <RemoveStaffDialog staff={staff} rows={rows} meId={meId} />
      <TemporaryPasswordDialog
        open={!!pw}
        title={pw?.created ? 'Account created' : 'Temporary password'}
        who={pw ? (pw.created ? pw.member : `${pw.member}: they were signed out everywhere`) : undefined}
        password={pw?.password}
        onClose={() => staff.setPending(null)}
      />
    </>
  );
}
