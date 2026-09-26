import type { StateCreator } from 'zustand';
import type { Connection, Container, Position, SavedFlow, Site, Subnet, TopologyData } from '@/types/topology';
import type { Catalog } from '@/catalog/catalog';
import type { Activity, Diagnostic, ImagesReport, Job } from '@/api/client';
import type { LayoutMode } from '@/canvas/layout';
import type { Scope } from '@/lib/topology';

export type DeployStatus = 'idle' | 'deploying' | 'deployed' | 'destroying' | 'error';
export type RuntimeStatus = 'running' | 'stopped' | 'paused';
export type Theme = 'system' | 'light' | 'dark';
export type Tool = 'select' | 'pan';
export type SidebarTab = 'palette' | 'explorer';

/** A link (by connection id) or a node (optionally one interface of it). */
export type CaptureDialogTarget =
  | { kind: 'link'; connectionId: string }
  | { kind: 'interface'; nodeId: string; interface?: string };

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
  /** Replace the traffic flows saved with the design (undoable). */
  setTrafficFlows: (flows: SavedFlow[]) => void;
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
  /** The most recent deploy/destroy job once it finished (for its log and steps). */
  lastJob: Job | null;
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
  setLastJob: (job: Job | null) => void;
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
  imagesOpen: boolean;
  /** Image ref to select when the Images sheet opens. */
  imagesFocus: string | null;
  /** Palette categories the user collapsed (persisted). */
  collapsedCategories: string[];
  /** The deploy/destroy job details popover (top bar). */
  jobDetailsOpen: boolean;
  /** What the "Capture packets" dialog is about to capture (null: closed). */
  captureDialog: CaptureDialogTarget | null;
  /** The captures & traffic runs sheet. */
  runsOpen: boolean;

  setZoom: (zoom: number) => void;
  setPurdueOpen: (open: boolean) => void;
  setCommandPaletteOpen: (open: boolean) => void;
  openImages: (focusRef?: string | null) => void;
  setImagesOpen: (open: boolean) => void;
  toggleCategory: (id: string) => void;
  setJobDetailsOpen: (open: boolean) => void;
  openCaptureDialog: (target: CaptureDialogTarget) => void;
  closeCaptureDialog: () => void;
  setRunsOpen: (open: boolean) => void;
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

/** A tab in the bottom dock. Ids are namespaced: term:<container>, cap:<job>, traffic:<job>|traffic:new. */
export type DockTab =
  | { kind: 'terminal'; id: string; containerId: string; name: string; ip?: string }
  | { kind: 'capture'; id: string; jobId: string; title: string }
  | { kind: 'traffic'; id: string; jobId: string | null; title: string; seed?: { client?: string; nonce: number } };

export interface DockSlice {
  dockTabs: DockTab[];
  activeDockTabId: string | null;
  dockMinimized: boolean;
  /** Open (or focus, updating it) a tab and show the dock. */
  openDockTab: (tab: DockTab) => void;
  /** Swap a tab for another in place (e.g. a new traffic run once it has a job). */
  replaceDockTab: (id: string, tab: DockTab) => void;
  closeDockTab: (id: string) => void;
  setActiveDockTab: (id: string) => void;
  setDockMinimized: (minimized: boolean) => void;
  openTerminal: (container: { id: string; name: string; ip?: string }) => void;
  closeTerminal: (containerId: string) => void;
}

export interface ActivitySlice {
  /** Captures and traffic runs running on the loaded topology (from /runtime). */
  activity: Activity[];
  setActivity: (activity: Activity[]) => void;
}

export interface CatalogSlice {
  catalog: Catalog | null;
  catalogStatus: 'idle' | 'loading' | 'ready' | 'error';
  loadCatalog: () => Promise<void>;
}

export interface ImagesSlice {
  /** Build support, sources and per-image status (null until first fetched). */
  images: ImagesReport | null;
  imagesError: string | null;
  setImagesReport: (report: ImagesReport | null, error?: string | null) => void;
}

export type AppState = TopologySlice & DocumentSlice & ViewSlice & DockSlice & ActivitySlice & CatalogSlice & ImagesSlice;

export type Mutators = [['zustand/devtools', never], ['zustand/persist', unknown], ['temporal', unknown], ['zustand/immer', never]];

export type SliceCreator<T> = StateCreator<AppState, Mutators, [], T>;
