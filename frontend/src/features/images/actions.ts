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

/** Add a Docker Hub namespace (URL or name); true if it was added. */
export async function addRegistry(url: string): Promise<boolean> {
  try {
    const reg = await api.addRegistry(url);
    toast.info(`Reading ${reg.namespace} from Docker Hub`, { description: 'Its images join the catalog when the sync ends.' });
    await refreshImages();
    return true;
  } catch (err) {
    toast.error('Could not add the registry', { description: api.errorMessage(err) });
    return false;
  }
}

export async function syncRegistry(reg: api.Registry): Promise<void> {
  try {
    await api.syncRegistry(reg.id);
    await refreshImages();
  } catch (err) {
    toast.error(`Could not sync ${reg.namespace}`, { description: api.errorMessage(err) });
  }
}

export async function removeRegistry(reg: api.Registry): Promise<void> {
  try {
    await api.removeRegistry(reg.id);
    toast.info(`Removed ${reg.namespace}`, { description: 'Nodes that use its images keep them; types it added deploy as plain hosts.' });
    await Promise.all([refreshImages(), useAppStore.getState().refreshCatalog()]);
  } catch (err) {
    toast.error(`Could not remove ${reg.namespace}`, { description: api.errorMessage(err) });
  }
}
