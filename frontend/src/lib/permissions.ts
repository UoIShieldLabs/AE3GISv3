// What the signed-in caller may do in the UI (classroom mode). The backend
// enforces every rule (api/access.py); this only hides what would be refused,
// and the authoring limits, which are the UI's own. Components check a
// capability, never a role.
import type { SessionUser } from '@/api/client';
import { useAppStore } from '@/store';

export type Capability =
  /** Write and edit tutorials (students run them). */
  | 'authorTutorials'
  /** Write and edit scenarios (students run them). */
  | 'authorScenarios'
  /** Build images, sync sources, add / sync / remove registries. */
  | 'manageImages'
  /** The labs on this host: reconcile, purge. */
  | 'manageHost'
  /** Publish topologies to students. */
  | 'publish'
  /** Class sign-up, join code, students. */
  | 'manageClass'
  /** Every topology, students' included. */
  | 'viewAllTopologies';

const ALL: Capability[] = ['authorTutorials', 'authorScenarios', 'manageImages', 'manageHost', 'publish', 'manageClass', 'viewAllTopologies'];

/** No user (accounts off before the first answer, tests) reads as the
 *  instructor, which is what accounts-off means. */
export function capabilitiesFor(user: SessionUser | null): ReadonlySet<Capability> {
  if (!user || user.role === 'instructor') return new Set(ALL);
  return new Set();
}

export function can(user: SessionUser | null, capability: Capability): boolean {
  return capabilitiesFor(user).has(capability);
}

export function useCan(capability: Capability): boolean {
  return useAppStore((s) => can(s.user, capability));
}

/** The caller is a student (classroom mode). */
export function useIsStudent(): boolean {
  return useAppStore((s) => s.user?.role === 'student');
}
