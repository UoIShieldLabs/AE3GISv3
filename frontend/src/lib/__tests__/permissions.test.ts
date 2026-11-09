import { describe, expect, it } from 'vitest';
import { can, capabilitiesFor } from '../permissions';

describe('capabilities', () => {
  it('gives the instructor everything, and accounts-off (no user) reads as the instructor', () => {
    const instructor = { id: 'i', username: 'instructor', role: 'instructor' as const };
    for (const user of [null, instructor]) {
      expect(can(user, 'authorTutorials')).toBe(true);
      expect(can(user, 'manageImages')).toBe(true);
      expect(can(user, 'publish')).toBe(true);
      expect(can(user, 'manageClass')).toBe(true);
    }
  });

  it('gives a student none of the instructor-only capabilities', () => {
    const student = { id: 's', username: 'alice', role: 'student' as const };
    expect(capabilitiesFor(student).size).toBe(0);
    expect(can(student, 'authorScenarios')).toBe(false);
    expect(can(student, 'manageHost')).toBe(false);
  });
});
