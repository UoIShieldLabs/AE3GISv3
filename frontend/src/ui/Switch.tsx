import { Switch as RSwitch, Checkbox as RCheckbox } from 'radix-ui';
import { Check, Minus } from 'lucide-react';
import { cn } from '@/lib/cn';

export function Switch({ className, ...props }: React.ComponentProps<typeof RSwitch.Root>) {
  return (
    <RSwitch.Root
      className={cn(
        'peer inline-flex h-4.5 w-8 shrink-0 cursor-pointer items-center rounded-full border border-transparent transition-colors',
        'bg-border-strong data-[state=checked]:bg-accent disabled:cursor-not-allowed disabled:opacity-50',
        'focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2',
        className,
      )}
      {...props}
    >
      <RSwitch.Thumb className="block size-3.5 translate-x-0.5 rounded-full bg-white shadow-sm transition-transform data-[state=checked]:translate-x-4" />
    </RSwitch.Root>
  );
}

export function Checkbox({ className, ...props }: React.ComponentProps<typeof RCheckbox.Root>) {
  return (
    <RCheckbox.Root
      className={cn(
        'peer flex size-4 shrink-0 items-center justify-center rounded border border-border-strong bg-surface transition-colors',
        'data-[state=checked]:border-accent data-[state=checked]:bg-accent data-[state=checked]:text-accent-fg',
        'data-[state=indeterminate]:border-accent data-[state=indeterminate]:bg-accent data-[state=indeterminate]:text-accent-fg',
        'disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-2 focus-visible:outline-ring focus-visible:outline-offset-2',
        className,
      )}
      {...props}
    >
      <RCheckbox.Indicator className="flex items-center justify-center">
        {props.checked === 'indeterminate' ? <Minus className="size-3" /> : <Check className="size-3" />}
      </RCheckbox.Indicator>
    </RCheckbox.Root>
  );
}
