import type { ImageStatus } from '@/api/client';
import { cn } from '@/lib/cn';
import { Badge, Tooltip } from '@/ui';
import { IMAGE_STATUS, statusLabel } from './status';

export function ImageStatusBadge({ image }: { image: ImageStatus }) {
  const meta = IMAGE_STATUS[image.status];
  return (
    <Tooltip content={image.reason}>
      <Badge tone={meta.tone} dot={meta.pulse ? 'pulse' : true}>{statusLabel(image)}</Badge>
    </Tooltip>
  );
}

/** A small status dot (palette rows, picker options). */
export function ImageStatusDot({ image, className }: { image: ImageStatus | undefined; className?: string }) {
  if (!image) return null;
  const meta = IMAGE_STATUS[image.status];
  return (
    <span
      className={cn('inline-block size-1.5 shrink-0 rounded-full', meta.dot, meta.pulse && 'animate-pulse', className)}
      title={`${statusLabel(image)} — ${image.reason}`}
      aria-label={statusLabel(image)}
    />
  );
}
