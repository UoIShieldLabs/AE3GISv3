// What the signed-in caller may do in the UI. The backend enforces every rule
// (api/access.py); this only hides what would be refused, and the authoring
// limits, which are the UI's own. Components check a capability, never a role.
import type { SessionUser } from '@/api/client';
import { useAppStore } from '@/store';

export type Capability =
  /** Write and edit tutorials (students run them). */
  | 'authorTutorials'
  /** Write and edit scenarios (students run them). */
  | 'authorScenarios'
  /** Build images and sync build sources. */
  | 'manageImages'
  /** Add, sync and remove Docker Hub registries (they change everyone's catalog). */
  | 'manageRegistries'
  /** The labs on this host: reconcile, purge. */
  | 'manageHost'
  /** Publish your topologies to your students. */
  | 'publish'
  /** Your class: sign-up, join code, students. */
  | 'manageClass'
  /** Staff accounts: add admins and instructors, roles, resets, removal. */
  | 'manageUsers';

const STAFF: Capability[] = ['authorTutorials', 'authorScenarios', 'manageImages', 'publish', 'manageClass'];
const ADMIN: Capability[] = [...STAFF, 'manageRegistries', 'manageHost', 'manageUsers'];

/** No user (accounts off before the first answer, tests) reads as an admin,
 *  which is what accounts-off means. */
export function capabilitiesFor(user: SessionUser | null): ReadonlySet<Capability> {
  if (!user || user.role === 'admin') return new Set(ADMIN);
  if (user.role === 'instructor') return new Set(STAFF);
  return new Set();
}

export function can(user: SessionUser | null, capability: Capability): boolean {
  return capabilitiesFor(user).has(capability);
}

export function useCan(capability: Capability): boolean {
  return useAppStore((s) => can(s.user, capability));
}

/** The caller is a student. */
export function useIsStudent(): boolean {
  return useAppStore((s) => s.user?.role === 'student');
}
