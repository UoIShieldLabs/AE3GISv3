import type { DeployStatus, DocumentSlice, SliceCreator } from '../types';

const KNOWN: DeployStatus[] = ['idle', 'deploying', 'deployed', 'destroying', 'error'];

export const createDocumentSlice: SliceCreator<DocumentSlice> = (set) => ({
  backendId: null,
  backendName: null,
  deployStatus: 'idle',
  containerStatus: {},
  lastError: null,
  busy: false,

  setBackendInfo: ({ id, name, status }) =>
    set((s) => {
      s.backendId = id;
      s.backendName = name;
      s.deployStatus = KNOWN.includes(status as DeployStatus) ? (status as DeployStatus) : 'idle';
    }, false, 'setBackendInfo'),

  setDeployStatus: (status, error = null) =>
    set((s) => {
      s.deployStatus = status;
      s.lastError = error;
    }, false, 'setDeployStatus'),

  setContainerStatuses: (statuses) => set({ containerStatus: statuses }, false, 'setContainerStatuses'),

  clearContainerStatuses: () => set({ containerStatus: {} }, false, 'clearContainerStatuses'),

  setBusy: (busy) => set({ busy }, false, 'setBusy'),

  clearBackend: () =>
    set((s) => {
      s.backendId = null;
      s.backendName = null;
      s.deployStatus = 'idle';
      s.containerStatus = {};
      s.lastError = null;
    }, false, 'clearBackend'),
});
