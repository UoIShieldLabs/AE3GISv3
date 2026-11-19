import { describe, expect, it } from 'vitest';
import type { PresetSummary, Student, TopologySummary } from '@/api/client';
import {
  buildLibrary, defaultSection, holdsLab, lessonCopy, matches, sectionCounts, sectionsFor, sortTopologies, viewTopologies,
} from '../model';

let clock = 0;
const topo = (id: string, extra: Partial<TopologySummary> = {}): TopologySummary => ({
  id, name: id, status: 'idle', version: 1, published: false, update_available: false, holds_lab: false,
  created_at: '2026-11-01T00:00:00Z', updated_at: `2026-11-01T00:00:${String(clock++ % 60).padStart(2, '0')}Z`,
  ...extra,
});
const owner = (id: string) => ({ id, username: id });
const student = (id: string, extra: Partial<Student> = {}): Student => ({
  id, username: id, created_at: '2026-11-01T00:00:00Z', labs: [], topology_count: 0, last_seen_at: null, ...extra,
});

// The instructor's lesson + draft, two students with copies / own work.
const lesson = topo('ICS lesson', { published: true });
const draft = topo('Draft', { status: 'deployed', holds_lab: true });
const aliceCopy = topo('ICS lesson (alice)', { owner: owner('alice'), source_id: lesson.id, status: 'deployed', holds_lab: true });
const aliceOwn = topo('Firewall test', { owner: owner('alice') });
// A failed deploy that still holds containers, and one that was cleaned up.
const bobCopy = topo('ICS lesson (bob)', { owner: owner('bob'), source_id: lesson.id, status: 'error', holds_lab: true });
const failed = topo('Failed', { status: 'error', holds_lab: false });
const ALL = [lesson, draft, aliceCopy, aliceOwn, bobCopy, failed];

describe('library sections', () => {
  it('has a rail per mode, students without Running', () => {
    expect(sectionsFor('instructor')).toEqual(['running', 'mine', 'lessons', 'students', 'presets']);
    expect(sectionsFor('student')).toEqual(['lessons', 'mine', 'presets']);
    expect(sectionsFor('open')).toEqual(['running', 'mine', 'presets']);
    expect(defaultSection('student')).toBe('lessons');
    expect(defaultSection('instructor')).toBe('mine');
  });

  it('splits the instructor’s view into own, published, running and students', () => {
    const lib = buildLibrary({ topologies: ALL, students: [student('alice'), student('carol')], userId: null, mode: 'instructor' });
    expect(lib.mine.map((t) => t.id)).toEqual([failed.id, draft.id, lesson.id]); // most recent first
    expect(lib.lessons.map((t) => t.id)).toEqual([lesson.id]);
    expect(lib.running.map((t) => t.id)).toEqual([bobCopy.id, aliceCopy.id, draft.id]);
    // Every student of the class, by name, plus owners missing from it (bob).
    expect(lib.students.map((s) => [s.username, s.topologies.length, s.running.length])).toEqual([
      ['alice', 2, 1], ['bob', 1, 1], ['carol', 0, 0],
    ]);
    expect(lib.lessonStats.get(lesson.id)).toEqual({ started: 2, running: 2 });
    expect(lessonCopy(lib.students[0], lesson.id)?.id).toBe(aliceCopy.id);
    expect(lessonCopy(lib.students[2], lesson.id)).toBeUndefined();
    expect(lib.names.get(lesson.id)).toBe('ICS lesson');
  });

  it('gives a student the lessons and their own work, copies reached from the lesson', () => {
    const mine = [lesson, aliceCopy, aliceOwn];
    const lib = buildLibrary({ topologies: mine, students: null, userId: 'alice', mode: 'student' });
    expect(lib.lessons.map((t) => t.id)).toEqual([lesson.id]);
    expect(lib.mine.map((t) => t.id)).toEqual([aliceOwn.id]);
    expect(lib.copies.get(lesson.id)?.id).toBe(aliceCopy.id);
    expect(lib.running).toEqual([]);
    expect(lib.students).toEqual([]);
  });

  it('accounts off: everything is the caller’s, no lessons or students', () => {
    const lib = buildLibrary({ topologies: [lesson, draft], students: null, userId: null, mode: 'open' });
    expect(lib.mine).toHaveLength(2);
    expect(lib.lessons).toEqual([]);
    expect(lib.running.map((t) => t.id)).toEqual([draft.id]);
  });

  it('counts what holds a lab: the backend’s flag, else the status', () => {
    expect(holdsLab(bobCopy)).toBe(true); // error, still holding containers
    expect(holdsLab(failed)).toBe(false); // error, cleaned up
    const old = (status: string) => { const t = topo('x', { status }); delete (t as Partial<TopologySummary>).holds_lab; return t; };
    expect(['deployed', 'deploying', 'destroying'].every((s) => holdsLab(old(s)))).toBe(true);
    expect(holdsLab(old('error'))).toBe(false);
    expect(holdsLab(old('idle'))).toBe(false);
  });
});

describe('library search and sort', () => {
  it('matches every term, any case, across the texts given', () => {
    expect(matches('', 'x')).toBe(true);
    expect(matches('ics ALICE', 'ICS lesson', 'alice')).toBe(true);
    expect(matches('ics carol', 'ICS lesson', 'alice')).toBe(false);
  });

  it('counts what matches per section, students by name or topology', () => {
    const lib = buildLibrary({ topologies: ALL, students: [student('carol')], userId: null, mode: 'instructor' });
    const presets: PresetSummary[] = [
      { id: 'p1', name: 'ICS Scenario B', description: 'IEC-104', scenario_count: 1, site_count: 2 },
      { id: 'p2', name: 'Two-Subnet Demo', description: '', scenario_count: 0, site_count: 1 },
    ];
    expect(sectionCounts(lib, presets, '')).toEqual({ running: 3, mine: 3, lessons: 1, students: 3, presets: 2 });
    // "firewall" is alice's own topology: she matches, and nothing else does.
    expect(sectionCounts(lib, presets, 'firewall')).toEqual({ running: 0, mine: 0, lessons: 0, students: 1, presets: 0 });
    // Owner names are searchable in topology sections.
    expect(sectionCounts(lib, presets, 'bob').running).toBe(1);
    expect(sectionCounts(lib, presets, 'iec').presets).toBe(1);
  });

  it('sorts by recent, name (numeric) and status (running first)', () => {
    const a = topo('Lab 10'), b = topo('lab 2', { status: 'deployed' }), c = topo('Alpha', { status: 'error' });
    expect(sortTopologies([a, b, c], 'recent').map((t) => t.name)).toEqual(['Alpha', 'lab 2', 'Lab 10']);
    expect(sortTopologies([a, b, c], 'name').map((t) => t.name)).toEqual(['Alpha', 'lab 2', 'Lab 10']);
    expect(sortTopologies([a, b, c], 'status').map((t) => t.name)).toEqual(['lab 2', 'Alpha', 'Lab 10']);
  });

  it('filters running only by the lab that counts (a lesson: its copy)', () => {
    const copies = new Map([[lesson.id, aliceCopy]]);
    const other = topo('Other lesson', { published: true });
    const labOf = (t: TopologySummary) => copies.get(t.id);
    expect(viewTopologies([lesson, other], { q: '', sort: 'recent', runningOnly: true, labOf }).map((t) => t.id)).toEqual([lesson.id]);
    expect(viewTopologies([lesson, other], { q: 'other', sort: 'recent' }).map((t) => t.id)).toEqual([other.id]);
  });
});
