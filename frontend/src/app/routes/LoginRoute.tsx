import { useEffect, useState } from 'react';
import { Navigate, useNavigate, useSearchParams } from 'react-router';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { GraduationCap, LogIn } from 'lucide-react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { restoreSession, signIn, signUp } from '@/features/auth/actions';
import { AppearanceMenu } from '@/shell/AppearanceMenu';
import { Button, Checkbox, Field, Input, Spinner, Tabs, TabsContent, TabsList, TabsTrigger } from '@/ui';

const signInSchema = z.object({
  username: z.string().trim().min(1, 'Enter your username'),
  password: z.string().min(1, 'Enter your password'),
});
type SignInValues = z.infer<typeof signInSchema>;

const joinSchema = z.object({
  joinCode: z.string().trim().min(1, 'Enter the code your instructor shared'),
  username: z
    .string()
    .trim()
    .regex(/^[A-Za-z0-9][A-Za-z0-9._-]{2,31}$/, '3–32 characters: letters, digits, “.”, “_” or “-”'),
  password: z.string().min(8, 'At least 8 characters'),
});
type JoinValues = z.infer<typeof joinSchema>;

/** Only same-app paths, never an absolute URL from the query string. */
function safeNext(raw: string | null): string {
  return raw && raw.startsWith('/') && !raw.startsWith('//') ? raw : '/';
}

/** Sign in, or join the class with the instructor's code (classroom mode). */
export function LoginRoute() {
  const status = useAppStore((s) => s.authStatus);
  const authRequired = useAppStore((s) => s.authRequired);
  const signupOpen = useAppStore((s) => s.signupOpen);
  const [params] = useSearchParams();
  const next = safeNext(params.get('next'));

  useEffect(() => {
    if (status === 'unknown') void restoreSession();
  }, [status]);

  if (status === 'unknown') {
    return (
      <div className="flex h-full items-center justify-center bg-app">
        <Spinner />
      </div>
    );
  }
  if (status === 'signedIn' || authRequired === false) return <Navigate to={next} replace />;

  return (
    <div className="flex h-full flex-col bg-app">
      <header className="flex h-12 shrink-0 items-center gap-3 border-b border-border bg-surface px-4">
        <span className="ae-brand text-sm font-semibold tracking-tight">AE3GIS</span>
        <div className="ml-auto"><AppearanceMenu /></div>
      </header>
      <div className="flex min-h-0 flex-1 items-start justify-center overflow-y-auto px-4 py-16">
        <div className="w-full max-w-sm rounded-xl border border-border bg-surface p-6 shadow-sm">
          <h1 className="text-base font-semibold">Welcome</h1>
          <p className="mt-1 text-xs text-fg-muted">Sign in to this AE3GIS lab, or join your class with the code your instructor shared.</p>
          <Tabs defaultValue="signin" className="mt-5">
            <TabsList variant="pills" className="w-full">
              <TabsTrigger value="signin" className="flex-1 justify-center"><LogIn /> Sign in</TabsTrigger>
              <TabsTrigger value="join" className="flex-1 justify-center"><GraduationCap /> Join class</TabsTrigger>
            </TabsList>
            <TabsContent value="signin" className="pt-4">
              <SignInForm next={next} />
            </TabsContent>
            <TabsContent value="join" className="pt-4">
              {signupOpen ? (
                <JoinForm next={next} />
              ) : (
                <p className="rounded-md border border-dashed border-border-strong p-3 text-xs text-fg-muted">
                  Sign-up is closed right now. Ask your instructor to open it, then reload this page.
                </p>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

function RememberMe({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-fg-muted">
      <Checkbox checked={checked} onCheckedChange={(v) => onChange(v === true)} />
      Keep me signed in on this device
    </label>
  );
}

function SignInForm({ next }: { next: string }) {
  const navigate = useNavigate();
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<SignInValues>({
    resolver: zodResolver(signInSchema),
    defaultValues: { username: '', password: '' },
  });
  const submit = async (v: SignInValues) => {
    setError(null);
    try {
      await signIn(v.username, v.password, remember);
      void navigate(next, { replace: true });
    } catch (err) {
      setError(api.errorMessage(err, 'Could not sign in'));
    }
  };
  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-3" noValidate>
      <Field label="Username" error={errors.username?.message}>
        {(ctl) => <Input {...ctl} {...register('username')} autoComplete="username" autoFocus />}
      </Field>
      <Field label="Password" error={errors.password?.message}>
        {(ctl) => <Input {...ctl} {...register('password')} type="password" autoComplete="current-password" />}
      </Field>
      <RememberMe checked={remember} onChange={setRemember} />
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <Button type="submit" variant="primary" loading={isSubmitting}>Sign in</Button>
    </form>
  );
}

function JoinForm({ next }: { next: string }) {
  const navigate = useNavigate();
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<JoinValues>({
    resolver: zodResolver(joinSchema),
    defaultValues: { joinCode: '', username: '', password: '' },
  });
  const submit = async (v: JoinValues) => {
    setError(null);
    try {
      await signUp(v.username, v.password, v.joinCode, remember);
      void navigate(next, { replace: true });
    } catch (err) {
      setError(api.errorMessage(err, 'Could not create your account'));
    }
  };
  return (
    <form onSubmit={handleSubmit(submit)} className="flex flex-col gap-3" noValidate>
      <Field label="Join code" error={errors.joinCode?.message} hint="From your instructor, e.g. kq7m-x3fa">
        {(ctl) => <Input {...ctl} {...register('joinCode')} mono autoComplete="off" autoFocus />}
      </Field>
      <Field label="Choose a username" error={errors.username?.message}>
        {(ctl) => <Input {...ctl} {...register('username')} autoComplete="username" />}
      </Field>
      <Field label="Choose a password" error={errors.password?.message}>
        {(ctl) => <Input {...ctl} {...register('password')} type="password" autoComplete="new-password" />}
      </Field>
      <RememberMe checked={remember} onChange={setRemember} />
      {error ? <p role="alert" className="text-xs text-danger">{error}</p> : null}
      <Button type="submit" variant="primary" loading={isSubmitting}>Create account</Button>
    </form>
  );
}
