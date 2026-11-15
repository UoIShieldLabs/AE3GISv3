import type { DeployStatus, DocumentSlice, SliceCreator } from '../types';

const KNOWN: DeployStatus[] = ['idle', 'deploying', 'deployed', 'destroying', 'error'];

export const createDocumentSlice: SliceCreator<DocumentSlice> = (set) => ({
  backendId: null,
  backendName: null,
  version: null,
  deployStatus: 'idle',
  containerStatus: {},
  activeJob: null,
  lastJob: null,
  diagnostics: [],
  lastError: null,
  busy: false,
  savedState: null,
  deployedAt: null,
  destroyDialogOpen: false,
  owner: null,
  published: false,
  sourceId: null,
  updateAvailable: false,

  setBackendInfo: ({ id, name, status, version }) =>
    set((s) => {
      s.backendId = id;
      s.backendName = name;
      s.deployStatus = KNOWN.includes(status as DeployStatus) ? (status as DeployStatus) : 'idle';
      if (version !== undefined) s.version = version;
    }, false, 'setBackendInfo'),

  setVersion: (version) => set({ version }, false, 'setVersion'),

  setDeployStatus: (status, error = null) =>
    set((s) => {
      s.deployStatus = status;
      s.lastError = error;
    }, false, 'setDeployStatus'),

  setContainerStatuses: (statuses) => set({ containerStatus: statuses }, false, 'setContainerStatuses'),

  clearContainerStatuses: () => set({ containerStatus: {} }, false, 'clearContainerStatuses'),

  setActiveJob: (activeJob) => set({ activeJob }, false, 'setActiveJob'),

  setLastJob: (lastJob) => set({ lastJob }, false, 'setLastJob'),

  setDiagnostics: (diagnostics) => set({ diagnostics }, false, 'setDiagnostics'),

  setBusy: (busy) => set({ busy }, false, 'setBusy'),

  setSavedState: (savedState) => set({ savedState }, false, 'setSavedState'),

  setDeployedAt: (deployedAt) => set({ deployedAt }, false, 'setDeployedAt'),

  setDestroyDialogOpen: (destroyDialogOpen) => set({ destroyDialogOpen }, false, 'setDestroyDialogOpen'),

  setRecordMeta: (meta) => set({ ...meta }, false, 'setRecordMeta'),

  clearBackend: () =>
    set((s) => {
      s.backendId = null;
      s.backendName = null;
      s.version = null;
      s.deployStatus = 'idle';
      s.containerStatus = {};
      s.activeJob = null;
      s.lastJob = null;
      s.diagnostics = [];
      s.lastError = null;
      s.savedState = null;
      s.deployedAt = null;
      s.destroyDialogOpen = false;
      s.owner = null;
      s.published = false;
      s.sourceId = null;
      s.updateAvailable = false;
    }, false, 'clearBackend'),
});
