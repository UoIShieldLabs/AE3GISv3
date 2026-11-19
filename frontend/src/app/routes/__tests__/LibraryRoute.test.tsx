import { beforeEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider, useLocation } from 'react-router';
import type { PresetSummary, Student, TopologySummary } from '@/api/client';
import { useAppStore } from '@/store';
import { TooltipProvider } from '@/ui';
import { LibraryRoute } from '../LibraryRoute';

vi.mock('@/api/client', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/api/client')>();
  return {
    ...actual,
    listTopologies: vi.fn(),
    listPresets: vi.fn(),
    getClassSettings: vi.fn(),
    listStudents: vi.fn(),
  };
});
const api = await import('@/api/client');

const topo = (id: string, name: string, extra: Partial<TopologySummary> = {}): TopologySummary => ({
  id, name, status: 'idle', version: 1, published: false, update_available: false, holds_lab: false,
  created_at: '2026-11-01T00:00:00Z', updated_at: '2026-11-01T00:00:00Z', ...extra,
});
const student = (id: string): Student => ({
  id, username: id, created_at: '2026-11-01T00:00:00Z', labs: [], topology_count: 0, last_seen_at: null,
});

const LESSON = topo('l1', 'ICS lesson', { published: true });
const DRAFT = topo('d1', 'Draft', { status: 'deployed', holds_lab: true, updated_at: '2026-11-02T00:00:00Z' });
const ALICE = topo('a1', 'Firewall test', { owner: { id: 'alice', username: 'alice' } });
const PRESETS: PresetSummary[] = [{ id: 'two-subnet-demo', name: 'Two-Subnet Demo', description: 'Two LANs', scenario_count: 0, site_count: 1 }];

function Where() {
  const { search } = useLocation();
  return <output data-testid="search">{search}</output>;
}

async function renderLibrary(url = '/') {
  const router = createMemoryRouter(
    [{ path: '/', element: <><LibraryRoute /><Where /></> }, { path: '/t/:id', element: <Where /> }],
    { initialEntries: [url] },
  );
  render(<TooltipProvider><RouterProvider router={router} /></TooltipProvider>);
  await act(async () => {}); // the first loads
}

const rail = () => screen.getByRole('navigation', { name: 'Library sections' });
const railItems = () => within(rail()).getAllByRole('button').map((b) => b.textContent);
const search = () => screen.getByTestId('search').textContent;
const heading = () => screen.getByRole('heading', { level: 1 }).textContent;

function signIn(role: 'instructor' | 'student' | null) {
  useAppStore.setState({
    authRequired: role !== null,
    user: role === 'student' ? { id: 'alice', username: 'alice', role: 'student' } : role ? { id: null, username: 'instructor', role: 'instructor' } : null,
    libraryLayout: 'grid',
    librarySort: 'recent',
  });
}

beforeEach(() => {
  vi.mocked(api.listTopologies).mockResolvedValue([LESSON, DRAFT, ALICE]);
  vi.mocked(api.listPresets).mockResolvedValue({ presets: PRESETS });
  vi.mocked(api.getClassSettings).mockResolvedValue({ signup_open: true, join_code: 'ABC123' } as Awaited<ReturnType<typeof api.getClassSettings>>);
  vi.mocked(api.listStudents).mockResolvedValue({ max_labs: 1, students: [student('alice'), student('bob')] });
});

describe('LibraryRoute', () => {
  it('gives the instructor every section, opening on their own topologies', async () => {
    signIn('instructor');
    await renderLibrary();
    expect(railItems()).toEqual(['Running1', 'My topologies2', 'Lessons1', 'Students2', 'Presets1']);
    expect(heading()).toContain('My topologies');
    expect(screen.getByText('Draft')).toBeInTheDocument();
    expect(screen.queryByText('Firewall test')).not.toBeInTheDocument(); // a student's
  });

  it('gives a student their lessons first, and no Running or Students', async () => {
    signIn('student');
    vi.mocked(api.listTopologies).mockResolvedValue([LESSON, ALICE]);
    await renderLibrary();
    expect(railItems()).toEqual(['Lessons1', 'My topologies1', 'Presets1']);
    expect(heading()).toContain('Lessons');
    expect(screen.getByText('ICS lesson')).toBeInTheDocument();
  });

  it('keeps the section in the URL and opens a student from the table', async () => {
    signIn('instructor');
    await renderLibrary();
    fireEvent.click(within(rail()).getByRole('button', { name: /Students/ }));
    expect(search()).toBe('?s=students');
    const table = screen.getByRole('table');
    expect(within(table).getAllByRole('row').slice(1).map((r) => within(r).getAllByRole('cell')[0].textContent)).toEqual(['alice', 'bob']);
    // The students are listed under Students in the rail too.
    expect(within(rail()).getByRole('button', { name: /alice/ })).toBeInTheDocument();
    fireEvent.click(within(table).getByRole('button', { name: 'alice' }));
    expect(search()).toBe('?s=students&u=alice');
    expect(heading()).toBe('alice');
    expect(screen.getByText('Firewall test')).toBeInTheDocument();
  });

  it('searches the section, shows matches per section, and clears', async () => {
    signIn('instructor');
    await renderLibrary();
    fireEvent.change(screen.getByRole('textbox', { name: 'Search the library' }), { target: { value: 'firewall' } });
    expect(search()).toBe('?q=firewall');
    expect(railItems()).toEqual(['Running0', 'My topologies0', 'Lessons0', 'Students1', 'Presets0']);
    expect(screen.getByText('Nothing matches')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'Clear filters' }));
    expect(search()).toBe('');
    expect(screen.getByText('Draft')).toBeInTheDocument();
  });

  it('switches to the list layout and remembers it', async () => {
    signIn(null);
    vi.mocked(api.listTopologies).mockResolvedValue([LESSON, DRAFT]);
    await renderLibrary();
    expect(railItems()).toEqual(['Running1', 'Saved topologies2', 'Presets1']);
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'List' }));
    expect(useAppStore.getState().libraryLayout).toBe('list');
    expect(JSON.parse(localStorage.getItem('ae3gis.ui') ?? '{}').state.libraryLayout).toBe('list');
    expect(within(screen.getByRole('table')).getByText('Draft')).toBeInTheDocument();
  });

  it('starts from a preset in the New menu', async () => {
    signIn(null);
    vi.mocked(api.listTopologies).mockResolvedValue([]);
    await renderLibrary();
    fireEvent.keyDown(screen.getByRole('button', { name: 'More ways to start' }), { key: 'Enter' });
    const fromPreset = await screen.findByRole('menuitem', { name: /From preset/ });
    fireEvent.keyDown(fromPreset, { key: 'ArrowRight' });
    expect(await screen.findByRole('menuitem', { name: 'Two-Subnet Demo' })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /Import JSON/ })).toBeInTheDocument();
  });
});
