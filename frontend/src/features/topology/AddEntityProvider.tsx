import { useCallback, useMemo, useState } from 'react';
import type { Position } from '@/types/topology';
import { findSite, locate, suggestCidr, type Scope } from '@/lib/topology';
import { defaultImageFor } from '@/catalog/catalog';
import { useAppStore } from '@/store';
import { toast } from '@/ui';
import { AddEntityContext, type AddEntityApi } from './AddEntityContext';
import { AddSiteDialog } from './dialogs/AddSiteDialog';
import { AddSubnetDialog } from './dialogs/AddSubnetDialog';
import { AddDeviceDialog } from './dialogs/AddDeviceDialog';
import { BulkAddDevicesDialog } from './dialogs/BulkAddDevicesDialog';
import { BulkConnectionsDialog } from './dialogs/BulkConnectionsDialog';

type DialogState =
  | { kind: 'site'; at?: Position }
  | { kind: 'subnet'; siteId: string; at?: Position }
  | { kind: 'device'; subnetId: string; type?: string; image?: string; at?: Position }
  | { kind: 'bulk-devices'; subnetId: string }
  | { kind: 'bulk-connections'; scope: Scope };

/** Owns every "add …" dialog so the canvas, palette, menus and hotkeys share one flow. */
export function AddEntityProvider({ children }: { children: React.ReactNode }) {
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const topology = useAppStore((s) => s.topology);

  const requestAdd = useCallback<AddEntityApi['requestAdd']>((item, target, opts) => {
    const st = useAppStore.getState();
    if (item.kind === 'site') {
      if (target.siteId || target.subnetId) { toast.info('Sites live at the Network level.'); return; }
      setDialog({ kind: 'site', at: target.at });
    } else if (item.kind === 'subnet') {
      if (!target.siteId || target.subnetId) { toast.info('Pick a site first, or drop onto one.'); return; }
      setDialog({ kind: 'subnet', siteId: target.siteId, at: target.at });
    } else {
      if (!target.subnetId) { toast.info('Pick a subnet first, or drop onto one.'); return; }
      if (opts?.immediate) {
        const id = st.addContainer({ subnetId: target.subnetId, type: item.type, image: item.image, position: target.at });
        if (id) st.selectNodes([id]);
      } else {
        setDialog({ kind: 'device', subnetId: target.subnetId, type: item.type, image: item.image, at: target.at });
      }
    }
  }, []);

  const api = useMemo<AddEntityApi>(() => ({
    requestAdd,
    requestBulkDevices: (subnetId) => setDialog({ kind: 'bulk-devices', subnetId }),
    requestBulkConnections: (scope) => setDialog({ kind: 'bulk-connections', scope }),
  }), [requestAdd]);

  const close = (o: boolean) => { if (!o) setDialog(null); };
  const subnetFor = (id: string) => { const hit = locate(topology, id); return hit?.kind === 'subnet' ? hit.subnet : null; };

  return (
    <AddEntityContext.Provider value={api}>
      {children}
      <AddSiteDialog
        open={dialog?.kind === 'site'}
        onOpenChange={close}
        defaultName={`Site ${topology.sites.length + 1}`}
        onSubmit={(v) => {
          if (dialog?.kind !== 'site') return;
          const st = useAppStore.getState();
          st.selectNodes([st.addSite({ name: v.name, location: v.location, position: dialog.at })]);
        }}
      />
      <AddSubnetDialog
        open={dialog?.kind === 'subnet'}
        onOpenChange={close}
        defaultName={dialog?.kind === 'subnet' ? `Subnet ${(findSite(topology, dialog.siteId)?.subnets.length ?? 0) + 1}` : ''}
        defaultCidr={suggestCidr(topology)}
        onSubmit={(v) => {
          if (dialog?.kind !== 'subnet') return;
          const st = useAppStore.getState();
          const id = st.addSubnet({ siteId: dialog.siteId, name: v.name, cidr: v.cidr, position: dialog.at });
          if (id) st.selectNodes([id]);
        }}
      />
      <AddDeviceDialog
        open={dialog?.kind === 'device'}
        onOpenChange={close}
        subnet={dialog?.kind === 'device' ? subnetFor(dialog.subnetId) : null}
        presetType={dialog?.kind === 'device' ? dialog.type : undefined}
        presetImage={dialog?.kind === 'device' ? dialog.image : undefined}
        onSubmit={(v) => {
          if (dialog?.kind !== 'device') return;
          const st = useAppStore.getState();
          // No image = follow the type's default (as the inspector does).
          const image = v.image && v.image !== defaultImageFor(v.type) ? v.image : undefined;
          const id = st.addContainer({ subnetId: dialog.subnetId, name: v.name, type: v.type, ip: v.ip, image, position: dialog.at });
          if (id) st.selectNodes([id]);
        }}
      />
      <BulkAddDevicesDialog
        open={dialog?.kind === 'bulk-devices'}
        onOpenChange={close}
        subnet={dialog?.kind === 'bulk-devices' ? subnetFor(dialog.subnetId) : null}
      />
      <BulkConnectionsDialog
        open={dialog?.kind === 'bulk-connections'}
        onOpenChange={close}
        scope={dialog?.kind === 'bulk-connections' ? dialog.scope : null}
      />
    </AddEntityContext.Provider>
  );
}

