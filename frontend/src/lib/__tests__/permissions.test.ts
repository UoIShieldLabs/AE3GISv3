import { describe, expect, it } from 'vitest';
import type { SessionUser } from '@/api/client';
import { can, capabilitiesFor } from '../permissions';

const user = (role: SessionUser['role']): SessionUser => ({ id: role, username: role, role, must_change_password: false, env_managed: false });

describe('capabilities', () => {
  it('gives an admin everything, and accounts-off (no user) reads as an admin', () => {
    for (const u of [null, user('admin')]) {
      for (const c of ['authorTutorials', 'manageImages', 'manageRegistries', 'manageHost', 'publish', 'manageClass', 'manageUsers'] as const) {
        expect(can(u, c)).toBe(true);
      }
    }
  });

  it('gives an instructor their class and lessons, and image builds, but not the host', () => {
    const instructor = user('instructor');
    for (const c of ['authorTutorials', 'authorScenarios', 'manageImages', 'publish', 'manageClass'] as const) {
      expect(can(instructor, c)).toBe(true);
    }
    for (const c of ['manageRegistries', 'manageHost', 'manageUsers'] as const) {
      expect(can(instructor, c)).toBe(false);
    }
  });

  it('gives a student none of the staff capabilities', () => {
    const student = user('student');
    expect(capabilitiesFor(student).size).toBe(0);
    expect(can(student, 'authorScenarios')).toBe(false);
    expect(can(student, 'manageHost')).toBe(false);
  });
});
