// How each account role reads in the UI (badges in the user menu and the staff table).
import type { Role } from '@/api/client';

export const ROLE_TONE: Record<Role, 'accent' | 'info' | 'neutral'> = { admin: 'accent', instructor: 'info', student: 'neutral' };

export const ROLE_LABEL: Record<Role, string> = { admin: 'Admin', instructor: 'Instructor', student: 'Student' };
