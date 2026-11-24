import { UserRound } from 'lucide-react';
import { NavItem } from '@/ui';
import { cn } from '@/lib/cn';
import { staffMatches, studentMatches, type LibraryMode, type SectionId, type StaffRow, type StudentRow } from './model';
import { SECTION_ICON, sectionLabel } from './sections';

export interface LibraryRailProps {
  mode: LibraryMode;
  sections: SectionId[];
  /** What each section holds (what matches the search, while there is one);
   *  null while loading. */
  counts: Record<SectionId, number> | null;
  current: SectionId;
  /** The student (or, under Staff, the staff member) whose page is open. */
  student: string | null;
  /** Listed under Students while that section is open. */
  students: StudentRow[];
  /** Listed under Staff while that section is open (admin). */
  staff?: StaffRow[];
  q: string;
  onGo: (section: SectionId, opts?: { student?: string | null }) => void;
}

/** The library's sections: a column beside the content, a row of tabs on a
 *  narrow screen (where the students stay in the Students table). */
export function LibraryRail({ mode, sections, counts, current, student, students, staff = [], q, onGo }: LibraryRailProps) {
  const nested: (StudentRow | StaffRow)[] =
    current === 'students' ? students.filter((s) => studentMatches(s, q))
      : current === 'staff' ? staff.filter((s) => staffMatches(s, q)) : [];
  const paged = (id: SectionId) => id === 'students' || id === 'staff';
  return (
    <nav aria-label="Library sections" className="flex min-w-0 gap-0.5 overflow-x-auto text-xs [scrollbar-width:none] md:flex-col md:overflow-x-visible [&::-webkit-scrollbar]:hidden">
      {sections.map((id) => {
        const Icon = SECTION_ICON[id];
        const running = id === 'running' && !!counts?.running;
        return (
          <div key={id} className="contents md:flex md:flex-col md:gap-0.5">
            <NavItem
              icon={<Icon className={cn(running && 'text-success!')} />}
              label={sectionLabel(id, mode)}
              count={counts?.[id]}
              selected={current === id && !(paged(id) && student)}
              onClick={() => onGo(id)}
              className="w-auto shrink-0 md:w-full"
            />
            {id === current && paged(id) && nested.length > 0 ? (
              <div className="hidden max-h-[50vh] flex-col gap-0.5 overflow-y-auto md:flex">
                {nested.map((s) => (
                  <NavItem
                    key={s.id}
                    inset
                    icon={<UserRound />}
                    label={s.username}
                    count={s.topologies.length}
                    selected={student === s.id}
                    onClick={() => onGo(id, { student: s.id })}
                    adornment={s.running.length > 0 ? <span aria-label="running a lab" title="Running a lab" className="size-1.5 shrink-0 rounded-full bg-success" /> : null}
                  />
                ))}
              </div>
            ) : null}
          </div>
        );
      })}
    </nav>
  );
}
