import { Activity, FolderOpen, GraduationCap, LayoutTemplate, ShieldCheck, Users, type LucideIcon } from 'lucide-react';
import type { LibraryMode, SectionId } from './model';

export const SECTION_ICON: Record<SectionId, LucideIcon> = {
  running: Activity,
  mine: FolderOpen,
  lessons: GraduationCap,
  students: Users,
  staff: ShieldCheck,
  presets: LayoutTemplate,
};

export function sectionLabel(section: SectionId, mode: LibraryMode): string {
  switch (section) {
    case 'running': return 'Running';
    case 'mine': return mode === 'open' ? 'Saved topologies' : 'My topologies';
    case 'lessons': return 'Lessons';
    case 'students': return 'Students';
    case 'staff': return 'Staff';
    case 'presets': return 'Presets';
  }
}

export function sectionDescription(section: SectionId, mode: LibraryMode): string {
  switch (section) {
    case 'running':
      if (mode === 'admin') return 'Every lab on this host.';
      return mode === 'instructor' ? 'Your labs and your students’.' : 'Labs on this host.';
    case 'mine': return mode === 'student' ? 'Topologies you made or duplicated.' : '';
    case 'lessons': return mode === 'student' ? 'From your instructor. Opening one starts your own copy.' : 'Published to your students. Each student works in their own copy.';
    case 'students': return '';
    case 'staff': return 'Admins and instructors. Each has their own class and join code.';
    case 'presets': return 'Start a new topology from a template.';
  }
}
