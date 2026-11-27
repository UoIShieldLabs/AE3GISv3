import { Copy, RotateCcw, Settings2 } from 'lucide-react';
import { Button, IconButton, Popover, PopoverContent, PopoverTrigger, Spinner, Switch } from '@/ui';
import { useAgentStore } from '@/features/agent/agentStore';
import type { ClassState } from './useClass';

/** The caller's class in one line (the join code to share, or that sign-up is
 *  closed) and its settings in a popover: sign-up, the code, the tutor. */
export function ClassBar({ cls }: { cls: ClassState }) {
  const { settings } = cls;
  if (!settings) return <Spinner className="size-4" />;
  const code = settings.signup_open ? settings.join_code : null;
  return (
    <div className="flex items-center gap-1.5">
      {code ? (
        <span className="flex items-center gap-1 rounded-md border border-border bg-surface py-0.5 pl-2 pr-0.5 text-xs">
          <span className="text-fg-muted">Join code</span>
          <code className="font-mono font-medium tracking-wider text-fg">{code}</code>
          <IconButton label="Copy join code" size="icon-xs" onClick={() => void cls.copyCode()}><Copy /></IconButton>
        </span>
      ) : (
        <span className="text-xs text-fg-subtle">Sign-up closed</span>
      )}
      <Popover>
        <PopoverTrigger asChild>
          <Button size="sm" variant="ghost"><Settings2 /> Class settings</Button>
        </PopoverTrigger>
        <PopoverContent align="end" className="flex w-80 flex-col gap-3 text-xs">
          <ClassSettings cls={cls} />
        </PopoverContent>
      </Popover>
    </div>
  );
}

function ClassSettings({ cls }: { cls: ClassState }) {
  const agentOn = useAgentStore((s) => !!s.status?.enabled);
  const settings = cls.settings!;
  return (
    <>
      <Setting
        title="Students can join"
        hint="With the join code. Accounts stay when you turn it off."
        checked={settings.signup_open}
        disabled={cls.busy === 'signup'}
        onChange={cls.setSignup}
      />
      {settings.join_code ? (
        <div className="flex flex-col gap-1 rounded-md bg-surface-2 p-2">
          <div className="flex items-center gap-1">
            <code className="flex-1 font-mono text-sm tracking-widest">{settings.join_code}</code>
            <IconButton label="Copy join code" size="icon-xs" onClick={() => void cls.copyCode()}><Copy /></IconButton>
            <Button size="xs" variant="ghost" onClick={cls.rotate} loading={cls.busy === 'rotate'}><RotateCcw /> New code</Button>
          </div>
          <span className="truncate text-2xs text-fg-subtle">Join at <span className="font-mono">{window.location.origin}/login</span></span>
        </div>
      ) : null}
      {agentOn ? (
        <Setting
          title="Tutor for students"
          hint="Explains their lab and gives hints; never changes anything. You can read their chats."
          checked={!!settings.tutor_enabled}
          disabled={cls.busy === 'tutor'}
          onChange={cls.setTutor}
        />
      ) : null}
    </>
  );
}

function Setting({ title, hint, checked, disabled, onChange }: { title: string; hint: string; checked: boolean; disabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <label className="flex cursor-pointer items-start gap-2.5">
      <Switch checked={checked} disabled={disabled} onCheckedChange={onChange} aria-label={title} className="mt-0.5" />
      <span className="min-w-0">
        <span className="block text-[13px] font-medium text-fg">{title}</span>
        <span className="text-2xs text-fg-muted">{hint}</span>
      </span>
    </label>
  );
}
