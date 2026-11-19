import { useCallback, useEffect, useRef, useState } from 'react';
import * as api from '@/api/client';
import { toast } from '@/ui';

// Students sign in, deploy and leave while the instructor watches.
const POLL_MS = 5000;

export type ClassPending =
  | { kind: 'remove'; student: { id: string; username: string } }
  | { kind: 'password'; student: string; password: string };

/** The instructor's class (sign-up, join code, students) and what can be
 *  done to it. Loads once when enabled, then polls while `polling`. */
export function useClass({ enabled, polling, onChanged }: {
  /** Classroom mode, as the instructor. */
  enabled: boolean;
  /** The class is on screen. */
  polling: boolean;
  /** After a student was removed (the library refreshes). */
  onChanged?: () => void;
}) {
  const [settings, setSettings] = useState<api.ClassSettings | null>(null);
  const [students, setStudents] = useState<api.Students | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [pending, setPending] = useState<ClassPending | null>(null);
  // One toast per outage, not one per poll.
  const failed = useRef(false);

  const refresh = useCallback(async () => {
    try {
      const [c, s] = await Promise.all([api.getClassSettings(), api.listStudents()]);
      setSettings(c);
      setStudents(s);
      failed.current = false;
    } catch (err) {
      if (!failed.current) toast.error('Could not load the class', { description: api.errorMessage(err) });
      failed.current = true;
    }
  }, []);

  useEffect(() => {
    if (enabled) void refresh();
  }, [enabled, refresh]);

  useEffect(() => {
    if (!enabled || !polling) return;
    void refresh();
    const timer = setInterval(() => void refresh(), POLL_MS);
    return () => clearInterval(timer);
  }, [enabled, polling, refresh]);

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

  return {
    settings,
    students,
    busy,
    pending,
    setPending,
    refresh,
    setSignup: (signup_open: boolean) =>
      void run('signup', async () => setSettings(await api.updateClassSettings({ signup_open })), 'Could not change sign-up'),
    rotate: () =>
      void run('rotate', async () => setSettings(await api.updateClassSettings({ rotate_join_code: true })), 'Could not make a new code'),
    copyCode: async () => {
      if (!settings?.join_code) return;
      try {
        await navigator.clipboard.writeText(settings.join_code);
        toast.success('Join code copied');
      } catch {
        toast.info(settings.join_code);
      }
    },
    resetPassword: (student: { id: string; username: string }) =>
      void run(`pw:${student.id}`, async () => {
        const { password } = await api.resetStudentPassword(student.id);
        setPending({ kind: 'password', student: student.username, password });
      }, 'Could not reset the password'),
    remove: (student: { id: string; username: string }) =>
      void run(`rm:${student.id}`, async () => {
        setPending(null);
        await api.removeStudent(student.id);
        toast.success(`Removed ${student.username}`);
        await refresh();
        onChanged?.();
      }, 'Could not remove the student'),
  };
}

export type ClassState = ReturnType<typeof useClass>;
