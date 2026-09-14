import { useMemo, useState } from 'react';
import { useAppStore } from '@/store';
import { hasConnection, type Scope } from '@/lib/topology';
import { scopeChildren, scopeConnections } from '@/canvas/layout';
import { Button, Checkbox, Dialog, Field, Select, Tabs, TabsList, TabsTrigger, toast } from '@/ui';

type Mode = 'star' | 'mesh' | 'chain';

export interface BulkConnectionsDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  scope: Scope | null;
}

export function BulkConnectionsDialog({ open, onOpenChange, scope }: BulkConnectionsDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Bulk connections" description="Link several nodes at once. Existing links are skipped." size="md">
      {open && scope ? <BulkConnForm scope={scope} onDone={() => onOpenChange(false)} /> : null}
    </Dialog>
  );
}

function BulkConnForm({ scope, onDone }: { scope: Scope; onDone: () => void }) {
  const topology = useAppStore((s) => s.topology);
  const nodes = useMemo(() => {
    const t = topology;
    const nameOf = (id: string): string => {
      for (const site of t.sites) {
        if (site.id === id) return site.name;
        for (const sn of site.subnets) {
          if (sn.id === id) return sn.name;
          const c = sn.containers.find((x) => x.id === id);
          if (c) return c.name;
        }
      }
      return id;
    };
    return scopeChildren(t, scope).map((c) => ({ id: c.id, name: nameOf(c.id) }));
  }, [topology, scope]);
  const existing = useMemo(() => scopeConnections(topology, scope), [topology, scope]);

  const [mode, setMode] = useState<Mode>('star');
  const [hub, setHub] = useState<string | undefined>(nodes[0]?.id);
  const [selected, setSelected] = useState<Set<string>>(() => new Set(nodes.map((n) => n.id)));
  const [chain, setChain] = useState<string[]>([]);

  const toggle = (id: string) => setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });

  const pairs = useMemo(() => {
    const out: [string, string][] = [];
    const seen = new Set<string>();
    const push = (a: string, b: string) => {
      if (a === b) return;
      const key = a < b ? `${a}|${b}` : `${b}|${a}`;
      if (seen.has(key) || hasConnection(existing, a, b)) return;
      seen.add(key);
      out.push([a, b]);
    };
    if (mode === 'star' && hub) for (const n of nodes) if (selected.has(n.id)) push(hub, n.id);
    if (mode === 'mesh') { const ids = nodes.filter((n) => selected.has(n.id)).map((n) => n.id); for (let i = 0; i < ids.length; i++) for (let j = i + 1; j < ids.length; j++) push(ids[i], ids[j]); }
    if (mode === 'chain') for (let i = 0; i < chain.length - 1; i++) push(chain[i], chain[i + 1]);
    return out;
  }, [mode, hub, selected, chain, nodes, existing]);

  const apply = () => {
    const st = useAppStore.getState();
    let n = 0;
    for (const [a, b] of pairs) if (st.addConnection({ from: a, to: b })) n++;
    toast.success(`Added ${n} connection${n === 1 ? '' : 's'}`);
    onDone();
  };

  const options = nodes.map((n) => ({ value: n.id, label: n.name }));

  return (
    <div className="flex flex-col gap-4">
      <Tabs value={mode} onValueChange={(v) => setMode(v as Mode)}>
        <TabsList variant="pills" className="w-fit">
          <TabsTrigger value="star">Star</TabsTrigger>
          <TabsTrigger value="mesh">Mesh</TabsTrigger>
          <TabsTrigger value="chain">Chain</TabsTrigger>
        </TabsList>
      </Tabs>

      {mode === 'star' ? (
        <Field label="Hub" hint="Every checked node links to the hub.">{(c) => <Select {...c} value={hub} onValueChange={setHub} options={options} />}</Field>
      ) : null}

      {mode !== 'chain' ? (
        <div className="max-h-56 overflow-auto rounded-lg border border-border">
          {nodes.map((n) => (
            <label key={n.id} className="flex cursor-pointer items-center gap-2 border-b border-border px-3 py-1.5 text-xs last:border-b-0 hover:bg-hover">
              <Checkbox checked={selected.has(n.id)} onCheckedChange={() => toggle(n.id)} disabled={mode === 'star' && n.id === hub} />
              <span className={n.id === hub && mode === 'star' ? 'text-fg-muted' : ''}>{n.name}</span>
            </label>
          ))}
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          <p className="text-xs text-fg-muted">Click nodes in order; each links to the next.</p>
          <div className="flex flex-wrap gap-1">
            {nodes.map((n) => (
              <Button key={n.id} size="xs" variant={chain.includes(n.id) ? 'primary' : 'outline'} onClick={() => setChain((c) => (c.includes(n.id) ? c.filter((x) => x !== n.id) : [...c, n.id]))}>
                {chain.includes(n.id) ? `${chain.indexOf(n.id) + 1}. ` : ''}{n.name}
              </Button>
            ))}
          </div>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-fg-muted">{pairs.length} new connection{pairs.length === 1 ? '' : 's'}</span>
        <div className="flex gap-2">
          <Button variant="ghost" onClick={onDone}>Cancel</Button>
          <Button variant="primary" onClick={apply} disabled={pairs.length === 0}>Add connections</Button>
        </div>
      </div>
    </div>
  );
}
