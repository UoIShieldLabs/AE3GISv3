import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import type { PacketSummary } from '@/api/client';
import { cn } from '@/lib/cn';

const ROW = 22;
const OVERSCAN = 12;

// Protocol families get a token colour; everything else stays muted.
function protoClass(proto: string): string {
  const p = proto.toUpperCase();
  if (p === 'ARP') return 'text-warning';
  if (p.startsWith('ICMP')) return 'text-info';
  if (p === 'TCP' || p === 'UDP') return 'text-fg-muted';
  if (p === '?' || p.startsWith('0X')) return 'text-fg-subtle';
  return 'text-accent'; // an application protocol (Modbus/TCP, DNS, HTTP, iperf3…)
}

export interface PacketTableProps {
  rows: readonly PacketSummary[];
  /** Keep the newest packet in view. Scrolling up turns it off. */
  follow: boolean;
  onFollowChange: (follow: boolean) => void;
}

/** A windowed packet list (only visible rows are rendered). */
export function PacketTable({ rows, follow, onFollowChange }: PacketTableProps) {
  const scroller = useRef<HTMLDivElement>(null);
  const [view, setView] = useState({ top: 0, height: 300 });
  const t0 = rows.length ? rows[0].ts : 0;

  useEffect(() => {
    const el = scroller.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setView((v) => ({ ...v, height: el.clientHeight })));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useLayoutEffect(() => {
    const el = scroller.current;
    if (el && follow) el.scrollTop = el.scrollHeight;
  }, [rows, follow]);

  const onScroll = () => {
    const el = scroller.current;
    if (!el) return;
    setView({ top: el.scrollTop, height: el.clientHeight });
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < ROW * 2;
    if (atBottom !== follow) onFollowChange(atBottom);
  };

  const start = Math.max(0, Math.floor(view.top / ROW) - OVERSCAN);
  const end = Math.min(rows.length, Math.ceil((view.top + view.height) / ROW) + OVERSCAN);
  const cols = 'grid grid-cols-[4.5rem_5.5rem_minmax(7rem,11rem)_minmax(7rem,11rem)_6.5rem_4rem_minmax(0,1fr)] gap-x-3 px-3';

  return (
    <div className="flex min-h-0 flex-1 flex-col font-mono text-2xs">
      <div className={cn(cols, 'h-6 shrink-0 items-center border-b border-border bg-surface-2/60 font-sans font-medium text-fg-muted')} role="row">
        <span className="text-right">No.</span>
        <span className="text-right">Time</span>
        <span>Source</span>
        <span>Destination</span>
        <span>Protocol</span>
        <span className="text-right">Length</span>
        <span>Info</span>
      </div>
      <div ref={scroller} onScroll={onScroll} className="relative min-h-0 flex-1 overflow-auto" role="table" aria-rowcount={rows.length}>
        <div style={{ height: rows.length * ROW }} />
        {rows.slice(start, end).map((p, i) => (
          <div
            key={p.n}
            role="row"
            className={cn(cols, 'absolute inset-x-0 items-center hover:bg-hover', (start + i) % 2 === 1 && 'bg-surface-2/30')}
            style={{ top: (start + i) * ROW, height: ROW }}
          >
            <span className="text-right text-fg-subtle">{p.n}</span>
            <span className="text-right text-fg-muted">{(p.ts - t0).toFixed(6)}</span>
            <span className="truncate" title={p.src}>{p.src}</span>
            <span className="truncate" title={p.dst}>{p.dst}</span>
            <span className={cn('truncate font-sans font-medium', protoClass(p.proto))}>{p.proto}</span>
            <span className="text-right text-fg-muted">{p.len}</span>
            <span className="truncate text-fg" title={p.info}>{p.info}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
