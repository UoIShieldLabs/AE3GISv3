import { useMemo, useState } from 'react';
import type { CaptureRequest } from '@/api/client';
import { useAppStore, type CaptureDialogTarget } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { locate } from '@/lib/topology';
import { Button, Dialog, DialogClose, Field, Input, Select, Switch } from '@/ui';
import { useDeployedInterfaces } from '@/features/deployment/useDeployedInterfaces';
import { startCapture } from './actions';

const FILTER_PRESETS = ['icmp', 'arp', 'tcp', 'udp', 'tcp port 502', 'not port 22'];
/** Headers only: enough for L2–L4 (and most of an ICS header) at a fraction of the size. */
const HEADERS_SNAPLEN = 128;

/** "Capture packets" on a link or a node interface. Opened through
 *  `openCaptureDialog` (canvas menus, inspector). */
export function StartCaptureDialog() {
  const target = useAppStore((s) => s.captureDialog);
  const close = useAppStore((s) => s.closeCaptureDialog);
  return (
    <Dialog
      open={!!target}
      onOpenChange={(open) => { if (!open) close(); }}
      title="Capture packets"
      description="Records to a pcap you can download or stream into Wireshark while it runs."
      size="md"
    >
      {target ? <CaptureForm target={target} onDone={close} /> : null}
    </Dialog>
  );
}

function CaptureForm({ target, onDone }: { target: CaptureDialogTarget; onDone: () => void }) {
  const topology = useAppStore((s) => s.topology);
  const { deployStatus } = useAppShallow((s) => ({ deployStatus: s.deployStatus }));
  const deployed = useDeployedInterfaces();
  const nameOf = (id?: string | null) => {
    if (!id) return '';
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };

  const link = target.kind === 'link' ? deployed?.links.find((l) => l.connection_id === target.connectionId) : undefined;
  const nodeIfaces = target.kind === 'interface' ? deployed?.nodes[target.nodeId] ?? [] : [];
  const [side, setSide] = useState<'from' | 'to'>('from');
  const [iface, setIface] = useState<string | undefined>(target.kind === 'interface' ? target.interface ?? undefined : undefined);
  const [filter, setFilter] = useState('');
  const [headersOnly, setHeadersOnly] = useState(false);
  const [minutes, setMinutes] = useState('');
  const [maxPackets, setMaxPackets] = useState('');
  const [busy, setBusy] = useState(false);

  const chosenIface = iface ?? nodeIfaces[0]?.name;
  const ends = link ? [link.from ?? link.endpoints[0]?.node, link.to ?? link.endpoints[1]?.node] : [];
  const ifaceOptions = useMemo(
    () => nodeIfaces.map((i) => ({ value: i.name, label: `${i.name}${i.peer_node_id ? ` ↔ ${nameOf(i.peer_node_id)}` : ''}${i.ip ? ` · ${i.ip}` : ''}` })),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [nodeIfaces, topology],
  );

  let problem: string | null = null;
  if (deployStatus !== 'deployed') problem = 'Deploy the topology first.';
  else if (!deployed) problem = null; // loading
  else if (target.kind === 'link' && !link) problem = 'This connection is not part of the deployed lab. Save and redeploy to capture it.';
  else if (target.kind === 'interface' && nodeIfaces.length === 0) problem = 'This device has no deployed interfaces.';

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (problem) return;
    const body: CaptureRequest = {
      target:
        target.kind === 'link'
          ? { kind: 'link', connection_id: target.connectionId, endpoint: side }
          : { kind: 'interface', node_id: target.nodeId, interface: chosenIface ?? 'eth0' },
      filter: filter.trim(),
      snaplen: headersOnly ? HEADERS_SNAPLEN : 0,
      max_seconds: minutes ? Math.max(1, Math.round(Number(minutes) * 60)) : null,
      max_packets: maxPackets ? Math.max(1, Math.round(Number(maxPackets))) : null,
      max_bytes: null,
      // A readable title for the tab and lists (the backend would use machine names).
      label:
        target.kind === 'link' && link
          ? `${nameOf(side === 'from' ? ends[0] : ends[1])} ↔ ${nameOf(side === 'from' ? ends[1] : ends[0])}`
          : `${nameOf(target.kind === 'interface' ? target.nodeId : '')} ${chosenIface ?? ''}`.trim(),
    };
    setBusy(true);
    const cap = await startCapture(body);
    setBusy(false);
    if (cap) onDone();
  };

  return (
    <form onSubmit={(e) => void submit(e)} className="flex flex-col gap-4">
      {target.kind === 'link' ? (
        <Field label="Capture from" hint="Either end sees everything on the link.">
          {(ctl) => (
            <Select
              id={ctl.id}
              value={side}
              onValueChange={(v) => setSide(v)}
              disabled={!link}
              options={[
                { value: 'from', label: link ? `${nameOf(ends[0])} (${link.endpoints.find((e) => e.node === ends[0])?.interface ?? '?'})` : 'From end' },
                { value: 'to', label: link ? `${nameOf(ends[1])} (${link.endpoints.find((e) => e.node === ends[1])?.interface ?? '?'})` : 'To end' },
              ]}
            />
          )}
        </Field>
      ) : (
        <Field label={`Interface of ${nameOf(target.nodeId)}`}>
          {(ctl) => <Select id={ctl.id} value={chosenIface} onValueChange={setIface} options={ifaceOptions} disabled={!nodeIfaces.length} mono />}
        </Field>
      )}

      <Field label="Filter" hint="A tcpdump (BPF) filter. Empty captures everything.">
        {(ctl) => (
          <div className="flex flex-col gap-1.5">
            <Input {...ctl} mono value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="e.g. icmp or tcp port 502" />
            <div className="flex flex-wrap gap-1">
              {FILTER_PRESETS.map((f) => (
                <button key={f} type="button" onClick={() => setFilter(f)} className="rounded border border-border px-1.5 py-px font-mono text-2xs text-fg-muted hover:bg-hover hover:text-fg">
                  {f}
                </button>
              ))}
            </div>
          </div>
        )}
      </Field>

      <Field label="Headers only" hint={`Keep the first ${HEADERS_SNAPLEN} bytes of each packet: much smaller files under heavy traffic.`} inline>
        {(ctl) => <Switch id={ctl.id} checked={headersOnly} onCheckedChange={setHeadersOnly} />}
      </Field>

      <div className="grid grid-cols-2 gap-3">
        <Field label="Stop after (minutes)" hint="Empty: until you stop it (server limit applies).">
          {(ctl) => <Input {...ctl} type="number" min={0.1} step="any" value={minutes} onChange={(e) => setMinutes(e.target.value)} placeholder="∞" />}
        </Field>
        <Field label="Stop after (packets)">
          {(ctl) => <Input {...ctl} type="number" min={1} value={maxPackets} onChange={(e) => setMaxPackets(e.target.value)} placeholder="∞" />}
        </Field>
      </div>

      {problem ? <div className="rounded-md bg-warning-soft px-3 py-2 text-xs text-warning">{problem}</div> : null}

      <div className="flex justify-end gap-2 pt-1">
        <DialogClose asChild><Button variant="ghost">Cancel</Button></DialogClose>
        <Button type="submit" variant="primary" loading={busy} disabled={!!problem || !deployed}>Start capture</Button>
      </div>
    </form>
  );
}
