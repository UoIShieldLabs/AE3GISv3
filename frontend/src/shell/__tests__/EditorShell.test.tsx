import { beforeEach, describe, expect, it } from 'vitest';
import { act, render, screen } from '@testing-library/react';
import { useAppStore } from '@/store';
import { EditorShell } from '../EditorShell';

function renderShell() {
  render(
    <EditorShell
      topBar={null}
      breadcrumb={null}
      canvas={<div>canvas</div>}
      inspector={<div>inspector</div>}
      tutorials={<div>tutorials</div>}
    />,
  );
}

beforeEach(() => useAppStore.setState({ inspectorOpen: true, tutorialsOpen: false, dockTabs: [] }));

describe('EditorShell right column', () => {
  it('shows the inspector alone by default', () => {
    renderShell();
    expect(screen.getByText('inspector')).toBeInTheDocument();
    expect(screen.queryByText('tutorials')).toBeNull();
  });

  it('stacks tutorials over the inspector, and keeps either one alone', () => {
    renderShell();
    act(() => useAppStore.setState({ tutorialsOpen: true }));
    const tutorials = screen.getByText('tutorials');
    const inspector = screen.getByText('inspector');
    expect(tutorials.compareDocumentPosition(inspector) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    act(() => useAppStore.setState({ inspectorOpen: false }));
    expect(screen.getByText('tutorials')).toBe(tutorials); // not remounted
    expect(screen.queryByText('inspector')).toBeNull();
    act(() => useAppStore.setState({ tutorialsOpen: false }));
    expect(screen.queryByText('tutorials')).toBeNull();
  });
});
