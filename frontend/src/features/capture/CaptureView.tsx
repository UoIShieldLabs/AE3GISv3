import { useMemo, useState } from 'react';
import { ArrowDownToLine, Copy, Download, Radio, Square } from 'lucide-react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { locate } from '@/lib/topology';
import { Badge, Button, EmptyState, IconButton, Input, Popover, PopoverContent, PopoverTrigger, toast } from '@/ui';
import { useCaptureStream } from './useCaptureStream';
import { formatBps, formatBytes, matchesFilter } from './packetBuffer';
import { PacketTable } from './PacketTable';
import { detectPlatform, tcpdumpCommand, wiresharkCommand } from './wiresharkCommand';
import { downloadPcap, stopCapture } from './actions';

const STOPPED_BY: Record<string, string> = {
  user: 'Stopped',
  destroy: 'Stopped: the topology was destroyed',
  shutdown: 'Stopped: the server shut down',
  'limit:size': 'Stopped at the size limit',
  'limit:packets': 'Stopped at the packet limit',
  'limit:time': 'Stopped at the time limit',
  sidecar_exit: 'tcpdump exited',
};

function CopyLine({ label, text }: { label: string; text: string }) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center justify-between text-2xs font-medium text-fg-muted">
        {label}
        <button
          type="button"
          className="inline-flex items-center gap-1 text-accent hover:underline"
          onClick={() => void navigator.clipboard.writeText(text).then(() => toast.success('Copied'), () => toast.error('Could not copy'))}
        >
          <Copy className="size-3" /> Copy
        </button>
      </div>
      <code className="block max-h-24 overflow-auto rounded border border-border bg-surface-2 p-2 font-mono text-2xs break-all text-fg">{text}</code>
    </div>
  );
}

function WiresharkPopover({ jobId, live }: { jobId: string; live: boolean }) {
  const platform = detectPlatform();
  const url = api.pcapUrl(jobId, live);
  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button size="sm" variant="secondary">Open in Wireshark</Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="flex w-[30rem] flex-col gap-3">
        <div className="text-xs text-fg-muted">
          {live
            ? 'Run this on your machine to watch the capture live in Wireshark (it keeps streaming until the capture stops).'
            : 'Run this on your machine to open the capture in Wireshark, or download the .pcap.'}
        </div>
        <CopyLine label="Wireshark" text={wiresharkCommand(url, platform)} />
        <CopyLine label="tcpdump" text={tcpdumpCommand(url, platform)} />
      </PopoverContent>
    </Popover>
  );
}

/** A capture in the dock: live packet list, counters, stop, pcap and Wireshark. */
export function CaptureView({ jobId }: { jobId: string }) {
  const backendId = useAppStore((s) => s.backendId);
  const topology = useAppStore((s) => s.topology);
  const nameOf = (id?: string | null) => {
    if (!id) return '';
    const hit = locate(topology, id);
    return hit?.kind === 'container' ? hit.container.name : id;
  };
  const { capture, status, rows, dropped, ended, connection } = useCaptureStream(backendId, jobId);
  const [filter, setFilter] = useState('');
  const [follow, setFollow] = useState(true);
  const visible = useMemo(() => (filter.trim() ? rows.filter((p) => matchesFilter(p, filter)) : rows), [rows, filter]);

  const live = !!capture?.live && !ended;
  const stats = capture?.stats;
  const packets = live ? (status?.packets ?? stats?.packets ?? 0) : (stats?.packets ?? status?.packets ?? 0);
  const fileBytes = live ? (status?.file_bytes ?? stats?.file_bytes) : (stats?.file_bytes ?? status?.file_bytes);
  const ep = capture?.endpoint;
  const failed = capture?.status === 'failed';
  const undecoded = status?.undecoded ?? stats?.undecoded ?? 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div className="flex h-9 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 text-xs">
        <Radio className="size-3.5 text-fg-muted" aria-hidden />
        <span className="font-medium text-fg">{ep ? `${nameOf(ep.node_id)} · ${ep.interface}` : 'Capture'}</span>
        {ep?.peer_node_id ? <span className="text-fg-subtle">↔ {nameOf(ep.peer_node_id)}</span> : null}
        {capture?.filter ? <Badge mono tone="outline">{capture.filter}</Badge> : null}
        {live ? <Badge tone="danger" dot="pulse">Live</Badge> : failed ? <Badge tone="danger">Failed</Badge> : capture ? <Badge>Stopped</Badge> : null}
        <span className="tabular-nums text-fg-muted">
          {packets.toLocaleString()} packets · {formatBytes(fileBytes)}
          {live && status ? ` · ${status.pps.toFixed(0)} pkt/s · ${formatBps(status.bps)}` : ''}
        </span>
        <div className="ml-auto flex items-center gap-1.5">
          <Input className="h-7 w-48 text-xs" placeholder="Filter rows…" value={filter} onChange={(e) => setFilter(e.target.value)} aria-label="Filter packets" />
          <IconButton label={follow ? 'Following new packets' : 'Follow new packets'} size="icon-sm" variant={follow ? 'secondary' : 'ghost'} onClick={() => setFollow(!follow)}>
            <ArrowDownToLine />
          </IconButton>
          <IconButton label="Download .pcap" size="icon-sm" onClick={() => downloadPcap(jobId)} disabled={!fileBytes}>
            <Download />
          </IconButton>
          <WiresharkPopover jobId={jobId} live={live} />
          {live ? <Button size="sm" variant="danger-soft" onClick={() => void stopCapture(jobId)}><Square /> Stop</Button> : null}
        </div>
      </div>
      {rows.length ? (
        <PacketTable rows={visible} follow={follow} onFollowChange={setFollow} />
      ) : (
        <EmptyState
          className="flex-1"
          icon={<Radio />}
          title={failed ? 'The capture failed' : live ? 'Waiting for packets…' : connection === 'connecting' ? 'Connecting…' : 'No packets captured'}
          description={
            failed
              ? capture?.job.error
              : live
                ? 'Traffic on this interface appears here as it happens. Try a ping across the link.'
                : undefined
          }
        />
      )}
      {(undecoded > 0 || dropped > 0 || (!live && capture?.stats.stopped_by)) ? (
        <div className="flex h-6 shrink-0 items-center gap-3 border-t border-border px-3 text-2xs text-fg-muted">
          {!live && capture?.stats.stopped_by ? <span>{STOPPED_BY[capture.stats.stopped_by] ?? capture.stats.stopped_by}</span> : null}
          {capture?.stats.dropped_by_kernel ? <span className="text-warning">{capture.stats.dropped_by_kernel.toLocaleString()} dropped by the kernel</span> : null}
          {undecoded > 0 ? <span>{undecoded.toLocaleString()} packets not listed (rate limit): the pcap has them all</span> : null}
          {dropped > 0 ? <span>{dropped} updates skipped (browser busy)</span> : null}
          <span className="ml-auto">Showing the last {rows.length.toLocaleString()} packets</span>
        </div>
      ) : null}
    </div>
  );
}
