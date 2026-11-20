import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { TooltipProvider } from '@/ui';
import { RequireAuth } from '../RequireAuth';

vi.mock('@/features/images/imagePolling', () => ({ installImageRefresh: vi.fn() }));

const user = (must: boolean) => ({ id: 'u1', username: 'tess', role: 'instructor' as const, must_change_password: must, env_managed: false });

function renderApp() {
  const router = createMemoryRouter(
    [{ element: <RequireAuth />, children: [{ path: '/', element: <p>The library</p> }] }],
    { initialEntries: ['/'] },
  );
  render(<TooltipProvider><RouterProvider router={router} /></TooltipProvider>);
}

afterEach(() => {
  vi.restoreAllMocks();
  useAppStore.setState({ authRequired: null, user: null, authStatus: 'unknown' });
});

describe('RequireAuth', () => {
  it('asks for a new password after a temporary one, then lets the app through', async () => {
    useAppStore.setState({ authRequired: true, authStatus: 'signedIn', user: user(true) });
    const change = vi.spyOn(api, 'changePassword').mockResolvedValue(undefined);
    vi.spyOn(api, 'getMe').mockResolvedValue({ user: user(false), auth_required: true });
    renderApp();
    expect(screen.getByRole('heading', { name: 'Choose a new password' })).toBeInTheDocument();
    expect(screen.queryByText('The library')).not.toBeInTheDocument();

    fireEvent.change(screen.getByLabelText('Temporary password'), { target: { value: 'temp-pass-1' } });
    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'short' } });
    fireEvent.click(screen.getByRole('button', { name: 'Set password' }));
    expect(screen.getByRole('alert')).toHaveTextContent('at least 8 characters');
    expect(change).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText('New password'), { target: { value: 'my-own-pass' } });
    await act(async () => { fireEvent.click(screen.getByRole('button', { name: 'Set password' })); });
    expect(change).toHaveBeenCalledWith('temp-pass-1', 'my-own-pass');
    expect(screen.getByText('The library')).toBeInTheDocument();
  });

  it('passes a signed-in tab with its own password straight through', () => {
    useAppStore.setState({ authRequired: true, authStatus: 'signedIn', user: user(false) });
    renderApp();
    expect(screen.getByText('The library')).toBeInTheDocument();
  });
});
