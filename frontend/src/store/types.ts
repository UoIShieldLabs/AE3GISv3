import type { StateCreator } from 'zustand';
import type { Connection, Container, Position, Site, Subnet, TopologyData } from '@/types/topology';
import type { Catalog } from '@/catalog/catalog';
import type { Diagnostic, Job } from '@/api/client';
import type { LayoutMode } from '@/canvas/layout';
import type { Scope } from '@/lib/topology';

export type DeployStatus = 'idle' | 'deploying' | 'deployed' | 'destroying' | 'error';
export type RuntimeStatus = 'running' | 'stopped' | 'paused';
export type Theme = 'system' | 'light' | 'dark';
export type Tool = 'select' | 'pan';
export type SidebarTab = 'palette' | 'explorer';

export interface Selection {
  nodeIds: string[];
  edgeIds: string[];
}

export interface AddSiteInput { name: string; location?: string; position?: Position }
export interface AddSubnetInput { siteId: string; name: string; cidr: string; position?: Position; /** Create the gateway router + switch (default true). */ autoInfra?: boolean }
export interface AddContainerInput {
  subnetId: string;
  type: string;
  name?: string;
  ip?: string;
  image?: string;
  position?: Position;
  metadata?: Record<string, string>;
  persistencePaths?: string[];
  config?: Record<string, unknown>;
}
export interface AddConnectionInput { from: string; to: string; label?: string }
export interface NodeMove { id: string; position: Position }

export interface TopologySlice {
  topology: TopologyData;
  dirty: boolean;
  /** Reference to the topology object as last saved/loaded; used to recompute `dirty` after undo/redo. */
  savedTopology: TopologyData | null;

  loadTopology: (data: unknown) => void;
  newTopology: (name?: string) => void;
  setTopologyMeta: (meta: { name?: string; description?: string }) => void;
  markClean: () => void;

  addSite: (input: AddSiteInput) => string;
  updateSite: (siteId: string, updates: Partial<Omit<Site, 'id' | 'subnets' | 'subnetConnections'>>) => void;
  addSubnet: (input: AddSubnetInput) => string | null;
  updateSubnet: (subnetId: string, updates: Partial<Omit<Subnet, 'id' | 'containers' | 'connections'>>) => void;
  addContainer: (input: AddContainerInput) => string | null;
  updateContainer: (containerId: string, updates: Partial<Omit<Container, 'id'>>) => void;
  addConnection: (input: AddConnectionInput) => string | null;
  updateConnection: (id: string, updates: Partial<Omit<Connection, 'id'>>) => void;
  deleteNodes: (ids: string[]) => void;
  deleteConnections: (ids: string[]) => void;
  /** Delete nodes and connections in one undoable step. */
  deleteItems: (nodeIds: string[], edgeIds: string[]) => void;
  duplicateNodes: (ids: string[]) => string[];
  moveNodes: (moves: NodeMove[]) => void;
  applyLayout: (scope: Scope, mode: LayoutMode, sizes?: ReadonlyMap<string, { width: number; height: number }>) => void;
}

export interface DocumentSlice {
  backendId: string | null;
  backendName: string | null;
  /** Server-side revision of the saved record; sent back on save for conflict detection. */
  version: number | null;
  deployStatus: DeployStatus;
  /** Live container state from the engine, keyed by container id. Never persisted in the topology. */
  containerStatus: Record<string, RuntimeStatus>;
  /** The deploy/destroy job currently running on the backend, with its steps. */
  activeJob: Job | null;
  /** Backend validation of the current design (errors block deploy). */
  diagnostics: Diagnostic[];
  lastError: string | null;
  /** A save/load/deploy/destroy request is in flight. */
  busy: boolean;

  setBackendInfo: (info: { id: string; name: string; status: string; version?: number }) => void;
  setVersion: (version: number) => void;
  setDeployStatus: (status: DeployStatus, error?: string | null) => void;
  setContainerStatuses: (statuses: Record<string, RuntimeStatus>) => void;
  clearContainerStatuses: () => void;
  setActiveJob: (job: Job | null) => void;
  setDiagnostics: (diagnostics: Diagnostic[]) => void;
  clearBackend: () => void;
  setBusy: (busy: boolean) => void;
}

export interface ViewSlice {
  theme: Theme;
  tool: Tool;
  snapToGrid: boolean;
  showMinimap: boolean;
  layoutMode: LayoutMode;
  sidebarTab: SidebarTab;
  sidebarOpen: boolean;
  inspectorOpen: boolean;
  /** Ids drawn expanded in place (group nodes). Per session, not persisted. */
  expanded: Record<string, true>;
  selection: Selection;
  /** Current canvas zoom (for the status bar). */
  zoom: number;
  purdueOpen: boolean;
  commandPaletteOpen: boolean;

  setZoom: (zoom: number) => void;
  setPurdueOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  setTheme: (theme: Theme) => void;
  setTool: (tool: Tool) => void;
  setSnapToGrid: (on: boolean) => void;
  setShowMinimap: (on: boolean) => void;
  setLayoutMode: (mode: LayoutMode) => void;
  setSidebarTab: (tab: SidebarTab) => void;
  setSidebarOpen: (open: boolean) => void;
  setInspectorOpen: (open: boolean) => void;
  toggleExpanded: (id: string) => void;
  setExpanded: (ids: string[], expanded: boolean) => void;
  collapseAll: () => void;
  setSelection: (selection: Selection) => void;
  selectNodes: (ids: string[]) => void;
  clearSelection: () => void;
}

export interface TerminalSession {
  id: string;
  name: string;
  ip?: string;
}

export interface TerminalSlice {
  terminals: TerminalSession[];
  activeTerminalId: string | null;
  terminalMinimized: boolean;
  openTerminal: (container: { id: string; name: string; ip?: string }) => void;
  closeTerminal: (id: string) => void;
  setActiveTerminal: (id: string) => void;
  setTerminalMinimized: (minimized: boolean) => void;
}

export interface CatalogSlice {
  catalog: Catalog | null;
  catalogStatus: 'idle' | 'loading' | 'ready' | 'error';
  loadCatalog: () => Promise<void>;
}

export type AppState = TopologySlice & DocumentSlice & ViewSlice & TerminalSlice & CatalogSlice;

export type Mutators = [['zustand/devtools', never], ['zustand/persist', unknown], ['temporal', unknown], ['zustand/immer', never]];

export type SliceCreator<T> = StateCreator<AppState, Mutators, [], T>;
