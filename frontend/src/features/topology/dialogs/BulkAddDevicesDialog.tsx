import { useMemo, useState } from 'react';
import { Trash2, Wand2 } from 'lucide-react';
import type { Subnet } from '@/types/topology';
import { useAppStore } from '@/store';
import { defaultImageFor, displayNameFor } from '@/catalog/catalog';
import { getAvailableIps, getSubnetCapacity, isIpInCidr, isValidIp } from '@/utils/validation';
import { nextName } from '@/lib/topology';
import { Button, Dialog, Field, IconButton, Input, toast } from '@/ui';
import { DeviceTypePicker } from '../DeviceTypePicker';

interface Row { key: number; name: string; type: string; ip: string; image: string }

export interface BulkAddDevicesDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  subnet: Subnet | null;
}

export function BulkAddDevicesDialog({ open, onOpenChange, subnet }: BulkAddDevicesDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={onOpenChange}
      title="Bulk add devices"
      description={subnet ? <>Generate several devices in <span className="font-medium text-fg">{subnet.name}</span> <span className="font-mono">{subnet.cidr}</span></> : undefined}
      size="lg"
    >
      {open && subnet ? <BulkForm subnet={subnet} onDone={() => onOpenChange(false)} /> : null}
    </Dialog>
  );
}

let nextKey = 1;

function BulkForm({ subnet, onDone }: { subnet: Subnet; onDone: () => void }) {
  const [type, setType] = useState('workstation');
  const [prefix, setPrefix] = useState(displayNameFor('workstation'));
  const [prefixTouched, setPrefixTouched] = useState(false);
  const [count, setCount] = useState('5');
  const [rows, setRows] = useState<Row[]>([]);

  const taken = useMemo(() => subnet.containers.map((c) => c.ip).filter(Boolean), [subnet]);
  const capacity = getSubnetCapacity(subnet.cidr);
  const free = Math.max(0, capacity - taken.length - rows.length);

  const changeType = (t: string) => {
    setType(t);
    if (!prefixTouched) setPrefix(displayNameFor(t));
  };

  const generate = () => {
    const n = Math.min(500, Math.max(1, parseInt(count, 10) || 0));
    const usedIps = [...taken, ...rows.map((r) => r.ip)];
    const ips = getAvailableIps(subnet.cidr, usedIps, n);
    if (ips.length === 0) { toast.error('No free IPs left in this subnet'); return; }
    if (ips.length < n) toast.warning(`Only ${ips.length} free IPs; generated that many.`);
    const names = [...subnet.containers.map((c) => c.name), ...rows.map((r) => r.name)];
    const generated: Row[] = [];
    for (const ip of ips) {
      const name = nextName(names, prefix.trim() || displayNameFor(type));
      names.push(name);
      generated.push({ key: nextKey++, name, type, ip, image: defaultImageFor(type) });
    }
    setRows((r) => [...r, ...generated]);
  };

  const update = (key: number, patch: Partial<Row>) => setRows((r) => r.map((row) => (row.key === key ? { ...row, ...patch } : row)));
  const remove = (key: number) => setRows((r) => r.filter((row) => row.key !== key));

  const ipError = (row: Row): string | null => {
    if (!isValidIp(row.ip)) return 'Invalid IP';
    if (!isIpInCidr(row.ip, subnet.cidr)) return 'Outside subnet';
    if (taken.includes(row.ip)) return 'In use';
    if (rows.some((r) => r.key !== row.key && r.ip === row.ip)) return 'Duplicate';
    return null;
  };
  const valid = rows.length > 0 && rows.every((r) => r.name.trim() && !ipError(r));

  const submit = () => {
    const st = useAppStore.getState();
    const ids: string[] = [];
    for (const r of rows) {
      const id = st.addContainer({ subnetId: subnet.id, name: r.name.trim(), type: r.type, ip: r.ip, image: r.image || undefined });
      if (id) ids.push(id);
    }
    if (ids.length) st.selectNodes(ids);
    toast.success(`Added ${ids.length} device${ids.length === 1 ? '' : 's'}`);
    onDone();
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-[1.4fr_1fr_80px_auto] items-end gap-2 rounded-lg border border-border bg-surface-2/60 p-3">
        <Field label="Type">{(c) => <DeviceTypePicker id={c.id} value={type} onValueChange={changeType} />}</Field>
        <Field label="Name prefix">{(c) => <Input {...c} value={prefix} onChange={(e) => { setPrefix(e.target.value); setPrefixTouched(true); }} />}</Field>
        <Field label="Count" hint={`${free} free`}>{(c) => <Input {...c} type="number" min={1} max={500} value={count} onChange={(e) => setCount(e.target.value)} />}</Field>
        <Button variant="secondary" onClick={generate} className="mb-[18px]"><Wand2 /> Generate</Button>
      </div>

      {rows.length === 0 ? (
        <p className="py-6 text-center text-xs text-fg-muted">Generate rows above, then tweak names or IPs before adding.</p>
      ) : (
        <div className="max-h-72 overflow-auto rounded-lg border border-border">
          <table className="w-full text-xs">
            <thead className="sticky top-0 bg-surface-2 text-left text-2xs uppercase tracking-wide text-fg-subtle">
              <tr><th className="px-2 py-1.5 font-medium">Name</th><th className="px-2 py-1.5 font-medium">Type</th><th className="px-2 py-1.5 font-medium">IP</th><th className="px-2 py-1.5 font-medium">Image</th><th className="w-8" /></tr>
            </thead>
            <tbody>
              {rows.map((r) => {
                const err = ipError(r);
                return (
                  <tr key={r.key} className="border-t border-border">
                    <td className="p-1"><Input value={r.name} onChange={(e) => update(r.key, { name: e.target.value })} className="h-7" aria-invalid={!r.name.trim() || undefined} /></td>
                    <td className="p-1 text-fg-muted">{displayNameFor(r.type)}</td>
                    <td className="p-1"><Input value={r.ip} mono onChange={(e) => update(r.key, { ip: e.target.value })} className="h-7" aria-invalid={err ? true : undefined} title={err ?? undefined} /></td>
                    <td className="p-1"><Input value={r.image} mono onChange={(e) => update(r.key, { image: e.target.value })} className="h-7" /></td>
                    <td className="p-1"><IconButton label="Remove" size="icon-xs" onClick={() => remove(r.key)}><Trash2 /></IconButton></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div className="flex items-center justify-between">
        <span className="text-xs text-fg-muted">{rows.length} pending · {taken.length}/{capacity} IPs used</span>
        <div className="flex gap-2">
          {rows.length ? <Button variant="ghost" onClick={() => setRows([])}>Clear</Button> : null}
          <Button variant="ghost" onClick={onDone}>Cancel</Button>
          <Button variant="primary" onClick={submit} disabled={!valid}>Add {rows.length || ''} device{rows.length === 1 ? '' : 's'}</Button>
        </div>
      </div>
    </div>
  );
}
