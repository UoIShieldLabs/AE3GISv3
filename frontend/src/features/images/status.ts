// Presentation of image statuses (GET /images) — one place for labels and tones.
import type { ImageStatus } from '@/api/client';
import { useAppStore } from '@/store';

export type ImageStatusKind = ImageStatus['status'];
type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

export const IMAGE_STATUS: Record<ImageStatusKind, { label: string; tone: Tone; dot: string; pulse?: boolean }> = {
  ready: { label: 'Ready', tone: 'success', dot: 'bg-success' },
  missing: { label: 'Not built', tone: 'neutral', dot: 'bg-fg-subtle' },
  stale: { label: 'Update available', tone: 'warning', dot: 'bg-warning' },
  building: { label: 'Building', tone: 'info', dot: 'bg-info', pulse: true },
  failed: { label: 'Build failed', tone: 'danger', dot: 'bg-danger' },
  unavailable: { label: "Can't build here", tone: 'danger', dot: 'bg-danger' },
  unmanaged: { label: 'Built manually', tone: 'neutral', dot: 'bg-success' },
};

/** Label for an image's status ("Not pulled" rather than "Not built" for registry images). */
export function statusLabel(img: Pick<ImageStatus, 'status' | 'kind'>): string {
  if (img.kind === 'registry' && img.status === 'missing') return 'Not pulled yet';
  return IMAGE_STATUS[img.status].label;
}

/** Needs someone's attention before (or after) a deploy. */
export function needsAttention(img: ImageStatus): boolean {
  return img.kind === 'build' && ['missing', 'stale', 'failed', 'unavailable'].includes(img.status);
}

/** Live status of one image ref (undefined until loaded, or for refs the catalog doesn't know). */
export function useImageStatus(ref: string | undefined): ImageStatus | undefined {
  return useAppStore((s) => (ref ? s.images?.images.find((i) => i.ref === ref) : undefined));
}

export function formatBytes(n: number | null | undefined): string {
  if (!n) return '—';
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)} GB`;
  return `${Math.round(n / 1e6)} MB`;
}
