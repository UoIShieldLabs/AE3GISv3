// The topology library's sections, as pure functions over the topology
// summaries (and, for the instructor, the class's students). The route only
// renders what these return.
import type { PresetSummary, Student, TopologySummary } from '@/api/client';

/** open: accounts off (everyone is the instructor). */
export type LibraryMode = 'open' | 'instructor' | 'student';
export type SectionId = 'running' | 'mine' | 'lessons' | 'students' | 'presets';
export type LibrarySort = 'recent' | 'name' | 'status';
export type LibraryLayout = 'grid' | 'list';

/** Statuses that hold a lab, are about to, or failed on the way (a failed
 *  deploy may still hold containers: destroy cleans it up). */
export const RUNNING_STATUSES: ReadonlySet<string> = new Set(['deployed', 'deploying', 'destroying', 'error']);
export const isRunning = (status: string | null | undefined): boolean => !!status && RUNNING_STATUSES.has(status);

/** The rail, in order. Students run one lab at most: no Running section. */
export function sectionsFor(mode: LibraryMode): SectionId[] {
  if (mode === 'student') return ['lessons', 'mine', 'presets'];
  if (mode === 'instructor') return ['running', 'mine', 'lessons', 'students', 'presets'];
  return ['running', 'mine', 'presets'];
}

export function defaultSection(mode: LibraryMode): SectionId {
  return mode === 'student' ? 'lessons' : 'mine';
}

export interface StudentRow {
  id: string;
  username: string;
  /** Their topologies (lesson copies included), most recent first. */
  topologies: TopologySummary[];
  /** Those holding a lab. */
  running: TopologySummary[];
  lastSeen: string | null;
}

export interface LessonStats {
  started: number;
  running: number;
}

export interface Library {
  /** Labs, the instructor's and the students' (not for a student). */
  running: TopologySummary[];
  /** The caller's own. A student's lesson copies are reached from the lesson. */
  mine: TopologySummary[];
  /** Instructor: what they published. Student: what they were given. */
  lessons: TopologySummary[];
  /** Instructor: every student (from the class, else from the topologies' owners), by name. */
  students: StudentRow[];
  /** A topology's name by id (the lesson a copy was made from). */
  names: Map<string, string>;
  /** Instructor: per lesson, how many students started it and how many run it. */
  lessonStats: Map<string, LessonStats>;
  /** Student: their copy of each lesson, by lesson id. */
  copies: Map<string, TopologySummary>;
}

const recent = (a: TopologySummary, b: TopologySummary) => b.updated_at.localeCompare(a.updated_at);

export function buildLibrary({ topologies, students, userId, mode }: {
  topologies: TopologySummary[];
  /** The class (instructor, classroom mode); null until it loads. */
  students: Student[] | null;
  userId: string | null | undefined;
  mode: LibraryMode;
}): Library {
  const all = topologies.slice().sort(recent);
  const student = mode === 'student';
  const mine = all.filter((t) => (student ? t.owner?.id === userId && !t.source_id : !t.owner));
  const lessons = student
    ? all.filter((t) => t.published && t.owner?.id !== userId)
    : mode === 'instructor' ? all.filter((t) => t.published && !t.owner) : [];
  const running = student ? [] : all.filter((t) => isRunning(t.status));

  const copies = new Map<string, TopologySummary>();
  const lessonStats = new Map<string, LessonStats>();
  const rows = new Map<string, StudentRow>();
  if (student) {
    for (const t of all) {
      if (t.source_id && t.owner?.id === userId && !copies.has(t.source_id)) copies.set(t.source_id, t);
    }
  } else if (mode === 'instructor') {
    for (const s of students ?? []) {
      rows.set(s.id, { id: s.id, username: s.username, topologies: [], running: [], lastSeen: s.last_seen_at ?? null });
    }
    for (const t of all) {
      if (!t.owner) continue;
      let row = rows.get(t.owner.id);
      if (!row) {
        row = { id: t.owner.id, username: t.owner.username, topologies: [], running: [], lastSeen: null };
        rows.set(t.owner.id, row);
      }
      row.topologies.push(t);
      if (isRunning(t.status)) row.running.push(t);
      if (t.source_id) {
        const stats = lessonStats.get(t.source_id) ?? { started: 0, running: 0 };
        stats.started += 1;
        if (isRunning(t.status)) stats.running += 1;
        lessonStats.set(t.source_id, stats);
      }
    }
  }

  return {
    running,
    mine,
    lessons,
    students: [...rows.values()].sort((a, b) => a.username.localeCompare(b.username)),
    names: new Map(all.map((t) => [t.id, t.name])),
    lessonStats,
    copies,
  };
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
export const studentMatches = (s: StudentRow, q: string) => matches(q, s.username, ...s.topologies.map((t) => t.name));
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
export function viewTopologies(items: TopologySummary[], { q, sort, runningOnly = false, statusOf = (t) => t.status }: {
  q: string;
  sort: LibrarySort;
  runningOnly?: boolean;
  /** The status shown (a student's lesson shows their copy's). */
  statusOf?: (t: TopologySummary) => string;
}): TopologySummary[] {
  const shown = items.filter((t) => topologyMatches(t, q) && (!runningOnly || isRunning(statusOf(t))));
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
    presets: presets.filter((p) => presetMatches(p, q)).length,
  };
}

/** A student's copy of a lesson (the most recent if there were several). */
export function lessonCopy(row: StudentRow, lessonId: string): TopologySummary | undefined {
  return row.topologies.find((t) => t.source_id === lessonId);
}
