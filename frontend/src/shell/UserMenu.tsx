import { useState } from 'react';
import { useNavigate } from 'react-router';
import { KeyRound, LogOut, UserRound } from 'lucide-react';
import { useAppStore } from '@/store';
import { signOut } from '@/features/auth/actions';
import { PasswordForm } from '@/features/auth/PasswordForm';
import { ROLE_TONE } from '@/lib/roles';
import {
  Badge, Button, Dialog, DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger, IconButton, toast,
} from '@/ui';

/** Who is signed in, change password, sign out (top bar, library). Hidden
 *  while accounts are off: everyone is an admin then. */
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
            <Badge tone={ROLE_TONE[user.role]}>{user.role}</Badge>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          {/* The environment's admin's password is the environment's. */}
          {!user.env_managed ? (
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
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Change password" size="sm">
      {open ? (
        <PasswordForm
          onCancel={() => onOpenChange(false)}
          onDone={() => {
            toast.success('Password changed', { description: 'Your other sign-ins have ended.' });
            onOpenChange(false);
          }}
        />
      ) : null}
    </Dialog>
  );
}
