// Image actions (build, sync, cancel) as plain functions, like deployment/actions.
import * as api from '@/api/client';
import { imageNameFor } from '@/catalog/catalog';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { refreshImages } from './imagePolling';

/** Start builds; images already building keep their running job. */
export async function buildImages(refs: string[], opts: { fresh?: boolean } = {}): Promise<api.Job[]> {
  if (!refs.length) return [];
  try {
    const jobs = await api.buildImages(refs, opts.fresh);
    const names = refs.map(imageNameFor);
    toast.info(`${opts.fresh ? 'Rebuilding' : 'Building'} ${names.length === 1 ? names[0] : `${names.length} images`}`, {
      description: names.length > 1 ? names.join(', ') : 'Follow the build in Images.',
      action: { label: 'Open', onClick: () => useAppStore.getState().openImages(refs[0]) },
    });
    await refreshImages();
    return jobs;
  } catch (err) {
    toast.error('Could not start the build', { description: api.errorMessage(err) });
    return [];
  }
}

export async function syncSource(name: string): Promise<void> {
  try {
    await api.syncSource(name);
    await refreshImages();
  } catch (err) {
    toast.error(`Could not sync ${name}`, { description: api.errorMessage(err) });
  }
}

export async function cancelJob(jobId: string, what = 'Job'): Promise<void> {
  try {
    await api.cancelJob(jobId);
    toast.info(`${what} cancelled`);
    await refreshImages();
  } catch (err) {
    toast.error(`Could not cancel`, { description: api.errorMessage(err) });
  }
}
