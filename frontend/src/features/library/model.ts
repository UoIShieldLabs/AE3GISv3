// The topology library's sections, as pure functions over the topology
// summaries (and, for staff, their students and, for an admin, the staff).
// The route only renders what these return.
import type { PresetSummary, StaffMember, Student, TopologySummary } from '@/api/client';

/** open: accounts off (everyone is an admin). */
export type LibraryMode = 'open' | 'admin' | 'instructor' | 'student';
export type SectionId = 'running' | 'mine' | 'lessons' | 'students' | 'staff' | 'presets';
export type LibrarySort = 'recent' | 'name' | 'status';
export type LibraryLayout = 'grid' | 'list';

const LAB_STATUSES: ReadonlySet<string> = new Set(['deployed', 'deploying', 'destroying']);

/** An admin or instructor (accounts on). */
export const isStaffMode = (mode: LibraryMode): boolean => mode === 'admin' || mode === 'instructor';

/** It holds (or may hold) containers on this host: the backend says so
 *  (`holds_lab`, which counts a failed deploy only while it still has engine
 *  state); without it, by status. */
export const holdsLab = (t: TopologySummary | null | undefined): boolean =>
  !!t && (t.holds_lab ?? LAB_STATUSES.has(t.status));

/** The rail, in order. Students run one lab at most: no Running section. */
export function sectionsFor(mode: LibraryMode): SectionId[] {
  if (mode === 'student') return ['lessons', 'mine', 'presets'];
  if (mode === 'admin') return ['running', 'mine', 'lessons', 'students', 'staff', 'presets'];
  if (mode === 'instructor') return ['running', 'mine', 'lessons', 'students', 'presets'];
  return ['running', 'mine', 'presets'];
}

export function defaultSection(mode: LibraryMode): SectionId {
  return mode === 'student' ? 'lessons' : 'mine';
}

export interface Person {
  id: string;
  username: string;
}

export interface StudentRow {
  id: string;
  username: string;
  /** The staff member whose class they are in (known from the class list). */
  instructor: Person | null;
  /** Their topologies (lesson copies included), most recent first. */
  topologies: TopologySummary[];
  /** Those holding a lab. */
  running: TopologySummary[];
  lastSeen: string | null;
}

export interface StaffRow {
  id: string;
  username: string;
  role: StaffMember['role'];
  /** The environment's admin (its password is the environment's). */
  envManaged: boolean;
  /** They have not replaced their temporary password yet. */
  mustChangePassword: boolean;
  studentCount: number;
  signupOpen: boolean;
  /** Their own topologies, most recent first. */
  topologies: TopologySummary[];
  running: TopologySummary[];
  lastSeen: string | null;
}

export interface LessonStats {
  started: number;
  running: number;
}

export interface Library {
  /** Labs (not for a student): staff see theirs and their students', an admin every lab. */
  running: TopologySummary[];
  /** The caller's own. A student's lesson copies are reached from the lesson. */
  mine: TopologySummary[];
  /** Staff: what they published. Student: what they were given. */
  lessons: TopologySummary[];
  /** Staff: their students (an admin: every student), by name. */
  students: StudentRow[];
  /** Admin: every admin and instructor, by name. */
  staff: StaffRow[];
  /** A topology's name by id (the lesson a copy was made from). */
  names: Map<string, string>;
  /** Staff: per lesson, how many students started it and how many run it. */
  lessonStats: Map<string, LessonStats>;
  /** Student: their copy of each lesson, by lesson id. */
  copies: Map<string, TopologySummary>;
}

const recent = (a: TopologySummary, b: TopologySummary) => b.updated_at.localeCompare(a.updated_at);

export function buildLibrary({ topologies, students, staff = null, userId, mode }: {
  topologies: TopologySummary[];
  /** The class (staff, accounts on); null until it loads. */
  students: Student[] | null;
  /** The staff accounts (admin); null until they load. */
  staff?: StaffMember[] | null;
  userId: string | null | undefined;
  mode: LibraryMode;
}): Library {
  const all = topologies.slice().sort(recent);
  const student = mode === 'student';
  const teaching = isStaffMode(mode);
  const ownedByMe = (t: TopologySummary) => !!userId && t.owner?.id === userId;
  const mine = student
    ? all.filter((t) => ownedByMe(t) && !t.source_id)
    : teaching ? all.filter(ownedByMe) : all;
  const lessons = student
    ? all.filter((t) => t.published && !ownedByMe(t))
    : teaching ? all.filter((t) => t.published && ownedByMe(t)) : [];
  const running = student ? [] : all.filter((t) => holdsLab(t));

  const copies = new Map<string, TopologySummary>();
  const lessonStats = new Map<string, LessonStats>();
  const rows = new Map<string, StudentRow>();
  const staffRows = new Map<string, StaffRow>();
  if (student) {
    for (const t of all) {
      if (t.source_id && ownedByMe(t) && !copies.has(t.source_id)) copies.set(t.source_id, t);
    }
  } else if (teaching) {
    for (const s of students ?? []) {
      rows.set(s.id, {
        id: s.id,
        username: s.username,
        instructor: s.instructor ?? null,
        topologies: [],
        running: [],
        lastSeen: s.last_seen_at ?? null,
      });
    }
    for (const m of mode === 'admin' ? staff ?? [] : []) {
      staffRows.set(m.id, {
        id: m.id,
        username: m.username,
        role: m.role,
        envManaged: m.env_managed,
        mustChangePassword: m.must_change_password,
        studentCount: m.student_count,
        signupOpen: m.signup_open,
        topologies: [],
        running: [],
        lastSeen: m.last_seen_at ?? null,
      });
    }
    for (const t of all) {
      if (!t.owner) continue;
      if (t.owner.role !== 'student') {
        const member = staffRows.get(t.owner.id);
        if (member) {
          member.topologies.push(t);
          if (holdsLab(t)) member.running.push(t);
        }
        continue;
      }
      let row = rows.get(t.owner.id);
      if (!row) {
        row = { id: t.owner.id, username: t.owner.username, instructor: null, topologies: [], running: [], lastSeen: null };
        rows.set(t.owner.id, row);
      }
      row.topologies.push(t);
      if (holdsLab(t)) row.running.push(t);
      if (t.source_id) {
        const stats = lessonStats.get(t.source_id) ?? { started: 0, running: 0 };
        stats.started += 1;
        if (holdsLab(t)) stats.running += 1;
        lessonStats.set(t.source_id, stats);
      }
    }
  }

  const byName = <T extends { username: string }>(a: T, b: T) => a.username.localeCompare(b.username);
  return {
    running,
    mine,
    lessons,
    students: [...rows.values()].sort(byName),
    staff: [...staffRows.values()].sort(byName),
    names: new Map(all.map((t) => [t.id, t.name])),
    lessonStats,
    copies,
  };
}

/** A staff member's students (from the rows, which an admin has for everyone). */
export function studentsOf(rows: StudentRow[], instructorId: string): StudentRow[] {
  return rows.filter((r) => r.instructor?.id === instructorId);
}

// ── Search, sort, counts ──────────────────────────────────────────────

/** Every whitespace-separated term of `q` appears in one of the texts (any case). */
export function matches(q: string, ...texts: (string | null | undefined)[]): boolean {
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  if (terms.length === 0) return true;
  const hay = texts.filter(Boolean).join('\n').toLowerCase();
  return terms.every((term) => hay.includes(term));
}

export const topologyMatches = (t: TopologySummary, q: string) => matches(q, t.name, t.owner?.username);
export const studentMatches = (s: StudentRow, q: string) =>
  matches(q, s.username, s.instructor?.username, ...s.topologies.map((t) => t.name));
export const staffMatches = (s: StaffRow, q: string) => matches(q, s.username, s.role, ...s.topologies.map((t) => t.name));
export const presetMatches = (p: PresetSummary, q: string) => matches(q, p.name, p.description);

const STATUS_RANK: Record<string, number> = { deployed: 0, deploying: 1, destroying: 2, error: 3, idle: 4 };

export function sortTopologies(
  items: TopologySummary[],
  sort: LibrarySort,
  statusOf: (t: TopologySummary) => string = (t) => t.status,
): TopologySummary[] {
  const out = items.slice();
  if (sort === 'name') {
    out.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true, sensitivity: 'base' }) || recent(a, b));
  } else if (sort === 'status') {
    const rank = (t: TopologySummary) => STATUS_RANK[statusOf(t)] ?? 5;
    out.sort((a, b) => rank(a) - rank(b) || recent(a, b));
  } else {
    out.sort(recent);
  }
  return out;
}

/** What a topology section shows: matching the search, running only if asked, sorted. */
export function viewTopologies(items: TopologySummary[], { q, sort, runningOnly = false, statusOf = (t) => t.status, labOf = (t) => t }: {
  q: string;
  sort: LibrarySort;
  runningOnly?: boolean;
  /** The status shown (a student's lesson shows their copy's). */
  statusOf?: (t: TopologySummary) => string;
  /** The topology whose lab counts (a student's lesson: their copy). */
  labOf?: (t: TopologySummary) => TopologySummary | null | undefined;
}): TopologySummary[] {
  const shown = items.filter((t) => topologyMatches(t, q) && (!runningOnly || holdsLab(labOf(t))));
  return sortTopologies(shown, sort, statusOf);
}

/** Each section's count in the rail: what matches the search. */
export function sectionCounts(lib: Library, presets: PresetSummary[], q: string): Record<SectionId, number> {
  const n = (items: TopologySummary[]) => items.filter((t) => topologyMatches(t, q)).length;
  return {
    running: n(lib.running),
    mine: n(lib.mine),
    lessons: n(lib.lessons),
    students: lib.students.filter((s) => studentMatches(s, q)).length,
    staff: lib.staff.filter((s) => staffMatches(s, q)).length,
    presets: presets.filter((p) => presetMatches(p, q)).length,
  };
}

/** A student's copy of a lesson (the most recent if there were several). */
export function lessonCopy(row: StudentRow, lessonId: string): TopologySummary | undefined {
  return row.topologies.find((t) => t.source_id === lessonId);
}
