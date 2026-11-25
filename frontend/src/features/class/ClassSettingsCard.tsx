import { Copy, RotateCcw } from 'lucide-react';
import { Button, IconButton, Spinner, Switch } from '@/ui';
import { useAgentStore } from '@/features/agent/agentStore';
import type { ClassState } from './useClass';

/** Sign-up to the caller's class and its join code, over the students table. */
export function ClassSettingsCard({ cls }: { cls: ClassState }) {
  const { settings } = cls;
  if (!settings) {
    return <div className="flex justify-center rounded-xl border border-border bg-surface p-4"><Spinner /></div>;
  }
  const joinUrl = `${window.location.origin}/login`;
  return (
    <div className="flex flex-col gap-3">
    <section aria-label="Sign-up" className="flex flex-col gap-3 rounded-xl border border-border bg-surface p-4 text-xs sm:flex-row sm:items-center sm:gap-6">
      <label className="flex shrink-0 cursor-pointer items-center gap-3">
        <Switch checked={settings.signup_open} disabled={cls.busy === 'signup'} onCheckedChange={cls.setSignup} aria-label="Students can join your class" />
        <span>
          <span className="block text-[13px] font-medium">Students can join your class</span>
          <span className="text-fg-muted">Accounts stay when you turn it off.</span>
        </span>
      </label>
      {settings.join_code ? (
        <div className="flex min-w-0 flex-wrap items-center gap-2 sm:ml-auto sm:justify-end">
          <code className="rounded-md bg-surface-2 px-3 py-1.5 font-mono text-base tracking-widest">{settings.join_code}</code>
          <IconButton label="Copy join code" size="icon-sm" onClick={() => void cls.copyCode()}><Copy /></IconButton>
          <Button size="xs" variant="ghost" onClick={cls.rotate} loading={cls.busy === 'rotate'}><RotateCcw /> New code</Button>
          <span className="w-full text-fg-muted sm:text-right">
            Join at <span className="font-mono">{joinUrl}</span>
            {settings.signup_open ? null : ' (closed now)'}
          </span>
        </div>
      ) : (
        <p className="text-fg-muted sm:ml-auto">Turn it on to get a join code.</p>
      )}
    </section>
    <TutorSwitch cls={cls} />
    </div>
  );
}

/** The agent's read-only tutor for this class's students (when the agent is
 *  configured on this instance). */
function TutorSwitch({ cls }: { cls: ClassState }) {
  const agentOn = useAgentStore((s) => !!s.status?.enabled);
  if (!agentOn || !cls.settings) return null;
  return (
    <section aria-label="Tutor" className="rounded-xl border border-border bg-surface p-4 text-xs">
      <label className="flex cursor-pointer items-center gap-3">
        <Switch checked={!!cls.settings.tutor_enabled} disabled={cls.busy === 'tutor'} onCheckedChange={cls.setTutor} aria-label="Students get the tutor" />
        <span>
          <span className="block text-[13px] font-medium">Students get the tutor</span>
          <span className="text-fg-muted">
            A read-only assistant that explains their lab and gives hints first; it never changes anything. You can read their chats from each student’s page.
          </span>
        </span>
      </label>
    </section>
  );
}
