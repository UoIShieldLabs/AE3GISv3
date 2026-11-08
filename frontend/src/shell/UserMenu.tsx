import { useState } from 'react';
import { useNavigate } from 'react-router';
import { KeyRound, LogOut, UserRound } from 'lucide-react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { signOut } from '@/features/auth/actions';
import {
  Badge, Button, Dialog, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger, Field, IconButton, Input, toast,
} from '@/ui';

/** Who is signed in, change password, sign out (top bar, library). Hidden
 *  while accounts are off: everyone is the instructor then. */
export function UserMenu() {
  const user = useAppStore((s) => s.user);
  const authRequired = useAppStore((s) => s.authRequired);
  const navigate = useNavigate();
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [confirmOut, setConfirmOut] = useState(false);
  if (!authRequired || !user) return null;

  const doSignOut = async () => {
    setConfirmOut(false);
    await signOut();
    void navigate('/login', { replace: true });
  };
  const requestSignOut = () => {
    if (useAppStore.getState().dirty) setConfirmOut(true);
    else void doSignOut();
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <IconButton label={`Signed in as ${user.username}`} size="icon-sm" className="ae-user-menu"><UserRound /></IconButton>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="min-w-52">
          <DropdownMenuLabel className="flex items-center justify-between gap-2">
            <span className="truncate">{user.username}</span>
            <Badge tone={user.role === 'instructor' ? 'accent' : 'neutral'}>{user.role}</Badge>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {user.role === 'student' ? (
            <DropdownMenuItem onSelect={() => setPasswordOpen(true)}><KeyRound /> Change password…</DropdownMenuItem>
          ) : null}
          <DropdownMenuItem onSelect={requestSignOut}><LogOut /> Sign out</DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <ChangePasswordDialog open={passwordOpen} onOpenChange={setPasswordOpen} />
      <Dialog
        open={confirmOut}
        onOpenChange={setConfirmOut}
        title="Sign out with unsaved changes?"
        description="Changes to the open topology that are not saved will be lost."
        size="sm"
        footer={
          <>
            <Button variant="ghost" onClick={() => setConfirmOut(false)}>Cancel</Button>
            <Button variant="danger" onClick={() => void doSignOut()}>Sign out</Button>
          </>
        }
      >
        <p className="text-xs text-fg-muted">Save first to keep them.</p>
      </Dialog>
    </>
  );
}

function ChangePasswordDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const close = (o: boolean) => {
    if (!o) { setCurrent(''); setNext(''); setError(null); }
    onOpenChange(o);
  };
  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (next.length < 8) { setError('The new password needs at least 8 characters'); return; }
    setBusy(true);
    setError(null);
    try {
      await api.changePassword(current, next);
      toast.success('Password changed', { description: 'Your other sign-ins have ended.' });
      close(false);
    } catch (err) {
      setError(api.errorMessage(err));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open={open} onOpenChange={close} title="Change password" size="sm">
      <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-3">
        <Field label="Current password">
          {(ctl) => <Input {...ctl} type="password" autoComplete="current-password" value={current} onChange={(e) => setCurrent(e.target.value)} autoFocus />}
        </Field>
        <Field label="New password" hint="At least 8 characters">
          {(ctl) => <Input {...ctl} type="password" autoComplete="new-password" value={next} onChange={(e) => setNext(e.target.value)} />}
        </Field>
        {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
        <div className="flex justify-end gap-2 pt-1">
          <Button type="button" variant="ghost" onClick={() => close(false)}>Cancel</Button>
          <Button type="submit" variant="primary" loading={busy}>Change password</Button>
        </div>
      </form>
    </Dialog>
  );
}
