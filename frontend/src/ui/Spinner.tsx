import { Loader2 } from 'lucide-react';
import { cn } from '@/lib/cn';

export function Spinner({ className, ...props }: React.ComponentProps<typeof Loader2>) {
  return <Loader2 className={cn('size-4 animate-spin text-fg-muted', className)} aria-label="Loading" {...props} />;
}
