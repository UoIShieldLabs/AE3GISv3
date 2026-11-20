import { LogOut } from 'lucide-react';
import { useAppStore } from '@/store';
import { AppearanceMenu } from '@/shell/AppearanceMenu';
import { Button, toast } from '@/ui';
import { refreshMe, signOut } from './actions';
import { PasswordForm } from './PasswordForm';

/** After signing in with a temporary password (a new account, a reset): the
 *  backend refuses everything else until it is replaced. */
export function ChoosePasswordScreen() {
  const user = useAppStore((s) => s.user);
  return (
    <div className="flex h-full flex-col bg-app">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
        <span className="ae-brand text-sm font-semibold tracking-tight">AE3GIS</span>
        <div className="ml-auto flex items-center gap-1">
          <AppearanceMenu />
          <Button size="sm" variant="ghost" onClick={() => void signOut()}><LogOut /> Sign out</Button>
        </div>
      </header>
      <div className="flex min-h-0 flex-1 items-start justify-center overflow-y-auto px-4 py-16">
        <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-base font-semibold">Choose a new password</h1>
          <p className="mt-1 mb-5 text-xs text-fg-muted">
            {user ? `${user.username}, you` : 'You'} signed in with a temporary password. Replace it with one only you know.
          </p>
          <PasswordForm
            currentLabel="Temporary password"
            submitLabel="Set password"
            onDone={async () => {
              await refreshMe();
              toast.success('Password set');
            }}
          />
        </div>
      </div>
    </div>
  );
}
