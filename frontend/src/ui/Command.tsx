import { Command as Cmdk } from 'cmdk';
import { Search } from 'lucide-react';
import { cn } from '@/lib/cn';

/** Styled cmdk primitives. Used by the command palette and by Combobox. */
export function Command({ className, ...props }: React.ComponentProps<typeof Cmdk>) {
  return (
    <Cmdk
      className={cn('flex h-full w-full flex-col overflow-hidden rounded-lg bg-elevated text-fg', className)}
      {...props}
    />
  );
}

export function CommandInput({ className, ...props }: React.ComponentProps<typeof Cmdk.Input>) {
  return (
    <div className="flex items-center gap-2 border-b border-border px-3" cmdk-input-wrapper="">
      <Search className="size-3.5 shrink-0 text-fg-subtle" />
      <Cmdk.Input
        className={cn(
          'flex h-9 w-full bg-transparent text-[13px] outline-none placeholder:text-fg-subtle disabled:opacity-50',
          className,
        )}
        {...props}
      />
    </div>
  );
}

export function CommandList({ className, ...props }: React.ComponentProps<typeof Cmdk.List>) {
  return <Cmdk.List className={cn('max-h-72 overflow-y-auto overflow-x-hidden p-1', className)} {...props} />;
}

export function CommandEmpty(props: React.ComponentProps<typeof Cmdk.Empty>) {
  return <Cmdk.Empty className="py-6 text-center text-xs text-fg-muted" {...props} />;
}

export function CommandGroup({ className, ...props }: React.ComponentProps<typeof Cmdk.Group>) {
  return (
    <Cmdk.Group
      className={cn(
        'overflow-hidden [&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:py-1 [&_[cmdk-group-heading]]:text-2xs [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:uppercase [&_[cmdk-group-heading]]:tracking-wide [&_[cmdk-group-heading]]:text-fg-subtle',
        className,
      )}
      {...props}
    />
  );
}

export function CommandSeparator({ className, ...props }: React.ComponentProps<typeof Cmdk.Separator>) {
  return <Cmdk.Separator className={cn('-mx-1 my-1 h-px bg-border', className)} {...props} />;
}

export interface CommandItemProps extends React.ComponentProps<typeof Cmdk.Item> {
  shortcut?: string;
}

export function CommandItem({ className, shortcut, children, ...props }: CommandItemProps) {
  return (
    <Cmdk.Item
      className={cn(
        'relative flex cursor-default select-none items-center gap-2 rounded-md px-2 py-1.5 text-[13px] outline-none',
        'data-[selected=true]:bg-hover data-[disabled=true]:pointer-events-none data-[disabled=true]:opacity-50',
        '[&_svg]:size-3.5 [&_svg]:shrink-0 [&_svg]:text-fg-muted',
        className,
      )}
      {...props}
    >
      {children}
      {shortcut ? <span className="ml-auto pl-4 font-mono text-2xs text-fg-subtle">{shortcut}</span> : null}
    </Cmdk.Item>
  );
}
