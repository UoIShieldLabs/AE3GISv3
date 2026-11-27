// How tool calls read in the chat: a label per tool, and a one-line summary.

/** How a tool reads in the chat. */
const LABELS: Record<string, string> = {
  list_topologies: 'List topologies',
  get_topology: 'Read topology',
  validate_topology: 'Validate',
  get_catalog: 'Read device catalog',
  create_topology: 'Create topology',
  edit_topology: 'Edit topology',
  duplicate_topology: 'Duplicate topology',
  delete_topology: 'Delete topology',
  get_lab_status: 'Check lab status',
  deploy: 'Deploy',
  destroy: 'Destroy lab',
  wait_for_job: 'Wait for job',
  get_job: 'Read job',
  stop_run: 'Stop run',
  list_activity: 'List running',
  run_in_node: 'Run command',
  start_background: 'Start background run',
  run_scenario_phase: 'Run scenario phase',
  start_capture: 'Start capture',
  get_packets: 'Read packets',
  start_traffic: 'Start traffic',
  start_monitor: 'Start monitor',
  monitor_snapshot: 'Read monitor',
  get_tutorial: 'Read tutorial',
  read_docs: 'Read docs',
  publish_topology: 'Publish',
  list_images: 'List images',
  build_images: 'Build images',
  list_labs: 'List host labs',
  purge_lab: 'Purge lab',
  open_in_editor: 'Open in editor',
  select_nodes: 'Select on canvas',
  open_view: 'Open view',
  arrange: 'Arrange canvas',
};

export function toolLabel(name: string): string {
  return LABELS[name] ?? name.replace(/_/g, ' ');
}

/** One line saying what the call does (its most telling argument). */
export function describeCall(name: string, input: unknown): string {
  const a = (input && typeof input === 'object' ? input : {}) as Record<string, unknown>;
  switch (name) {
    case 'run_in_node':
      return `${String(a.node ?? '')}$ ${String(a.command ?? '')}`;
    case 'edit_topology': {
      const ops = Array.isArray(a.ops) ? a.ops : [];
      const kinds = [...new Set(ops.map((o) => String((o as { op?: unknown }).op ?? '')))].slice(0, 4);
      return `${ops.length} change${ops.length === 1 ? '' : 's'}${kinds.length ? `: ${kinds.join(', ')}` : ''}`;
    }
    case 'start_background': {
      const items = Array.isArray(a.items) ? a.items : [];
      return items.map((i) => `${String((i as { node?: unknown }).node)}$ ${String((i as { command?: unknown }).command)}`).join(' · ');
    }
    case 'read_docs':
      return String(a.topic || 'topics');
    case 'create_topology':
      return String(a.name ?? '');
    case 'start_capture': {
      const t = (a.target ?? {}) as Record<string, unknown>;
      const where = t.kind === 'link' ? `link ${String(t.connection_id)}` : `${String(t.node_id)}:${String(t.interface)}`;
      return a.filter ? `${where} · ${String(a.filter)}` : where;
    }
  }
  for (const key of ['job_id', 'capture_id', 'monitor_id', 'phase_id', 'query', 'lab_hash', 'view', 'layout']) {
    if (typeof a[key] === 'string' && a[key]) return String(a[key]);
  }
  return '';
}
