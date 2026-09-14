import { Separator as RSeparator } from 'radix-ui';
import { cn } from '@/lib/cn';

export function Separator({ className, orientation = 'horizontal', decorative = true, ...props }: React.ComponentProps<typeof RSeparator.Root>) {
  return (
    <RSeparator.Root
      orientation={orientation}
      decorative={decorative}
      className={cn('shrink-0 bg-border', orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px', className)}
      {...props}
    />
  );
}
