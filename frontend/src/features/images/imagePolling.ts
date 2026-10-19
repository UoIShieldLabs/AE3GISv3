// One refresher app-wide for GET /images. Polls every couple of seconds while
// something is building or syncing, while the Images sheet is open, or while a
// deploy runs (its images step may be building); otherwise it refreshes on
// window focus and after jobs finish. Also announces builds and syncs as they
// end, and re-fetches the catalog when a registry changed it.
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { toast } from '@/ui';

const ACTIVE_MS = 2000;

let timer: ReturnType<typeof setTimeout> | null = null;
let inflight: Promise<void> | null = null;
let installed = false;

function busy(report: api.ImagesReport | null): boolean {
  return (
    !!report &&
    (report.images.some((i) => i.active_job) || report.sources.some((s) => s.active_job) || (report.registries ?? []).some((r) => r.active_job))
  );
}

/** Changes whenever a registry is added, removed or synced (by anyone). */
function registriesKey(report: api.ImagesReport | null): string {
  return (report?.registries ?? []).map((r) => `${r.id}@${r.synced_at ?? ''}`).join(',');
}

function announce(prev: api.ImagesReport | null, next: api.ImagesReport) {
  if (!prev) return;
  const before = new Map(prev.images.map((i) => [i.ref, i]));
  for (const img of next.images) {
    const was = before.get(img.ref);
    if (!was?.active_job || img.active_job) continue;
    const openImages = () => useAppStore.getState().openImages(img.ref);
    if (img.last_job?.status === 'succeeded') toast.success(`${img.display_name} image ready`, { description: img.ref });
    else if (img.last_job?.status === 'failed') {
      toast.error(`${img.display_name} build failed`, { description: img.last_job.error ?? undefined, duration: 10000, action: { label: 'View log', onClick: openImages } });
    }
  }
  const sources = new Map(prev.sources.map((s) => [s.name, s]));
  for (const src of next.sources) {
    if (!sources.get(src.name)?.active_job || src.active_job) continue;
    const job = src.last_job;
    if (job?.status === 'succeeded') {
      const compare = job.steps.find((s) => s.name === 'compare')?.message;
      toast.success(`Synced ${src.name}`, { description: compare ?? undefined });
    } else if (job?.status === 'failed') toast.error(`Sync of ${src.name} failed`, { description: job.error ?? undefined });
  }
  const registries = new Map((prev.registries ?? []).map((r) => [r.id, r]));
  for (const reg of next.registries ?? []) {
    if (!registries.get(reg.id)?.active_job || reg.active_job) continue;
    const job = reg.last_job;
    if (job?.status === 'succeeded') toast.success(`Synced ${reg.namespace}`, { description: registrySummary(reg) });
    else if (job?.status === 'failed') toast.error(`Sync of ${reg.namespace} failed`, { description: job.error ?? undefined });
  }
}

/** "3 images loaded · 1 rejected · 2 pending" for a registry. */
export function registrySummary(reg: api.Registry): string {
  const parts = [`${reg.loaded?.length ?? 0} image${reg.loaded?.length === 1 ? '' : 's'} loaded`];
  if (reg.rejected?.length) parts.push(`${reg.rejected.length} rejected`);
  if (reg.pending?.length) parts.push(`${reg.pending.length} pending`);
  return parts.join(' · ');
}

function schedule() {
  if (timer !== null) clearTimeout(timer);
  timer = null;
  const s = useAppStore.getState();
  if (s.imagesOpen || busy(s.images) || s.activeJob?.kind === 'deploy') {
    timer = setTimeout(() => void refreshImages(), ACTIVE_MS);
  }
}

/** Fetch image statuses now (coalesces concurrent calls). */
export function refreshImages(): Promise<void> {
  if (inflight) return inflight;
  inflight = (async () => {
    const st = useAppStore.getState();
    try {
      const report = await api.getImages();
      announce(st.images, report);
      const catalogChanged = !!st.images && registriesKey(st.images) !== registriesKey(report);
      useAppStore.getState().setImagesReport(report);
      // A registry sync (here or in another browser) changed the catalog.
      if (catalogChanged) void useAppStore.getState().refreshCatalog();
    } catch (err) {
      useAppStore.getState().setImagesReport(useAppStore.getState().images, api.errorMessage(err));
    } finally {
      inflight = null;
      schedule();
    }
  })();
  return inflight;
}

/** Wire the refresher to focus and store transitions (idempotent). */
export function installImageRefresh(): void {
  if (installed) return;
  installed = true;
  window.addEventListener('focus', () => void refreshImages());
  useAppStore.subscribe((s, prev) => {
    if (s.imagesOpen && !prev.imagesOpen) void refreshImages();
    if (s.activeJob && !prev.activeJob) schedule();
    if (!s.activeJob && prev.activeJob) void refreshImages();
  });
  void refreshImages();
}
