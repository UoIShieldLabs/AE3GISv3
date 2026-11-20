import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';
import { toast } from '@/ui';

const POLL_MS = 5000;

export interface StaffRef {
  id: string;
  username: string;
}

export type StaffPending =
  | { kind: 'add' }
  | { kind: 'remove'; member: StaffRef }
  | { kind: 'password'; member: string; password: string; created: boolean };

/** The staff accounts (admins only) and what can be done to them. Loads once
 *  when enabled, then polls while `polling`. */
export function useStaff({ enabled, polling, onChanged }: {
  /** Accounts on, as an admin. */
  enabled: boolean;
  /** The staff are on screen. */
  polling: boolean;
  /** After someone was removed (their work moved: the library refreshes). */
  onChanged?: () => void;
}) {
  const [staff, setStaff] = useState<api.StaffMember[] | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pending, setPending] = useState<StaffPending | null>(null);
  const failed = useRef(false);

  const refresh = useCallback(async () => {
    try {
      setStaff(await api.listStaff());
      failed.current = false;
    } catch (err) {
      if (!failed.current) toast.error('Could not load the staff', { description: api.errorMessage(err) });
      failed.current = true;
    }
  }, []);

  useEffect(() => {
    if (enabled) void refresh();
  }, [enabled, refresh]);

  useEffect(() => {
    if (!enabled || !polling) return;
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [enabled, polling, refresh]);

  /** Resolves true when `fn` succeeded. */
  const run = async (key: string, fn: () => Promise<void>, failure: string): Promise<boolean> => {
    setBusy(key);
    try {
      await fn();
      return true;
    } catch (err) {
      toast.error(failure, { description: api.errorMessage(err) });
      return false;
    } finally {
      setBusy(null);
    }
  };

  return {
    staff,
    busy,
    pending,
    setPending,
    refresh,
    /** Throws the API's error, so the form can show it next to its fields. */
    add: async (username: string, role: api.StaffRole) => {
      setBusy('add');
      try {
        const { user, password } = await api.createStaff(username, role);
        setPending({ kind: 'password', member: user.username, password, created: true });
        await refresh();
      } finally {
        setBusy(null);
      }
    },
    setRole: (member: StaffRef, role: api.StaffRole) =>
      void run(`role:${member.id}`, async () => {
        await api.setStaffRole(member.id, role);
        toast.success(`${member.username} is now ${role === 'admin' ? 'an admin' : 'an instructor'}`);
        await refresh();
      }, 'Could not change the role'),
    resetPassword: (member: StaffRef) =>
      void run(`pw:${member.id}`, async () => {
        const { password } = await api.resetStaffPassword(member.id);
        setPending({ kind: 'password', member: member.username, password, created: false });
        await refresh();
      }, 'Could not reset the password'),
    remove: (member: StaffRef, heir: StaffRef) =>
      run(`rm:${member.id}`, async () => {
        await api.deleteStaff(member.id, heir.id);
        setPending(null);
        toast.success(`Removed ${member.username}`, { description: `Their topologies and students are ${heir.username}’s now.` });
        await refresh();
        onChanged?.();
      }, 'Could not remove them'),
  };
}

export type StaffState = ReturnType<typeof useStaff>;
