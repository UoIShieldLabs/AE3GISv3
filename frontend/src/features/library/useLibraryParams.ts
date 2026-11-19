import { useCallback } from 'react';
import { useSearchParams } from 'react-router';
import { defaultSection, sectionsFor, type LibraryMode, type SectionId } from './model';

/** Where the library is, kept in the URL (`/?s=students&u=<id>&q=…`) so Back
 *  from the editor returns to the same view and a view can be linked. */
export interface LibraryLocation {
  section: SectionId;
  /** Students: one student's page. */
  student: string | null;
  /** Students: the lesson the table follows. */
  lesson: string | null;
  q: string;
  runningOnly: boolean;
}

function parse(params: URLSearchParams, available: readonly SectionId[], fallback: SectionId): LibraryLocation {
  const raw = params.get('s') as SectionId | null;
  const section = raw && available.includes(raw) ? raw : fallback;
  return {
    section,
    student: section === 'students' ? params.get('u') || null : null,
    lesson: section === 'students' ? params.get('lesson') || null : null,
    q: params.get('q') ?? '',
    runningOnly: params.get('running') === '1',
  };
}

function serialize(loc: LibraryLocation, fallback: SectionId): URLSearchParams {
  const p = new URLSearchParams();
  if (loc.section !== fallback) p.set('s', loc.section);
  if (loc.section === 'students' && loc.student) p.set('u', loc.student);
  if (loc.section === 'students' && loc.lesson) p.set('lesson', loc.lesson);
  if (loc.q) p.set('q', loc.q);
  if (loc.runningOnly) p.set('running', '1');
  return p;
}

export function useLibraryParams(mode: LibraryMode) {
  const [params, setParams] = useSearchParams();
  const loc = parse(params, sectionsFor(mode), defaultSection(mode));

  // A patch applies to the URL as last rendered: two updates in one event
  // would overwrite each other, so a combined change is one patch.
  const update = useCallback(
    (patch: Partial<LibraryLocation>, replace: boolean) =>
      setParams((prev) => {
        const fallback = defaultSection(mode);
        return serialize({ ...parse(prev, sectionsFor(mode), fallback), ...patch }, fallback);
      }, { replace }),
    [mode, setParams],
  );

  return {
    ...loc,
    /** Open a section (a new history entry); the search stays. */
    go: (section: SectionId, opts: { student?: string | null; lesson?: string | null } = {}) =>
      update({ section, student: opts.student ?? null, lesson: opts.lesson ?? null }, false),
    setQuery: (q: string) => update({ q }, true),
    setRunningOnly: (runningOnly: boolean) => update({ runningOnly }, true),
    setLesson: (lesson: string | null) => update({ lesson }, true),
    clearFilters: () => update({ q: '', runningOnly: false }, true),
  };
}
