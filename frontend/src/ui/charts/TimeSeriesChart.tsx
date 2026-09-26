import { useEffect, useMemo, useRef } from 'react';
import uPlot from 'uplot';
import 'uplot/dist/uPlot.min.css';
import './chart.css';
import { useResolvedTheme } from '@/app/theme';
import type { ChartData } from './types';

export interface TimeSeriesChartProps {
  title: string;
  /** Unit shown after values (e.g. "Mb/s", "%"). */
  unit: string;
  data: ChartData;
  height?: number;
  /** Fixed y-range minimum (default 0). */
  yMin?: number;
  /** A note under the title (e.g. "top 6 of 9"). */
  note?: string;
}

function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

const fmt = (v: number | null | undefined, unit: string) =>
  v === null || v === undefined || Number.isNaN(v) ? '–' : `${v >= 100 ? v.toFixed(0) : v >= 10 ? v.toFixed(1) : v.toFixed(2)} ${unit}`;

/** A small line chart over run time (seconds). Colours come from the
 *  --chart-N tokens, so it follows the theme; the legend shows each series'
 *  value under the cursor (and is hidden for a single series: the title names it). */
export function TimeSeriesChart({ title, unit, data, height = 150, yMin = 0, note }: TimeSeriesChartProps) {
  const host = useRef<HTMLDivElement>(null);
  const plot = useRef<uPlot | null>(null);
  const theme = useResolvedTheme();
  // Rebuild only when the set of series (or the theme) changes; data updates are cheap.
  const shape = data.series.map((s) => `${s.key}:${s.slot}:${s.dash ? 1 : 0}:${s.label}`).join('|');
  const aligned = useMemo(() => [data.x, ...data.series.map((s) => s.values)] as uPlot.AlignedData, [data]);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const grid = cssVar('--border');
    const axisText = cssVar('--fg-muted');
    const axis: uPlot.Axis = {
      stroke: axisText,
      grid: { stroke: grid, width: 1 },
      ticks: { stroke: grid, width: 1, size: 4 },
      font: '10px Inter Variable, ui-sans-serif, system-ui, sans-serif',
    };
    const opts: uPlot.Options = {
      width: Math.max(el.clientWidth, 200),
      height,
      scales: { x: { time: false }, y: { range: (_u, _min, max) => [yMin, Math.max(max * 1.1, yMin + 1e-9)] } },
      axes: [
        { ...axis, values: (_u, ticks) => ticks.map((t) => `${Math.round(t)}s`) },
        { ...axis, size: 44, values: (_u, ticks) => ticks.map((t) => (t >= 1000 ? `${(t / 1000).toFixed(1)}k` : `${+t.toFixed(2)}`)) },
      ],
      legend: { show: data.series.length >= 2, live: true },
      cursor: { drag: { x: false, y: false }, points: { size: 8, width: 2 } },
      series: [
        { label: 't', value: (_u, v) => (v === null ? '–' : `${v.toFixed(1)}s`) },
        ...data.series.map((s) => ({
          label: s.label,
          stroke: cssVar(`--chart-${s.slot}`),
          width: 2,
          dash: s.dash ? [6, 4] : undefined,
          spanGaps: true,
          points: { show: false },
          value: (_u: uPlot, v: number | null) => fmt(v, unit),
        })),
      ],
    };
    const u = new uPlot(opts, aligned, el);
    plot.current = u;
    const ro = new ResizeObserver(() => u.setSize({ width: Math.max(el.clientWidth, 200), height }));
    ro.observe(el);
    return () => {
      ro.disconnect();
      u.destroy();
      plot.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shape, theme, height, unit, yMin]);

  useEffect(() => {
    plot.current?.setData(aligned);
  }, [aligned]);

  const empty = data.x.length === 0;
  return (
    <figure className="flex min-w-0 flex-col gap-1">
      <figcaption className="flex items-baseline gap-2 text-xs">
        <span className="font-medium text-fg">{title}</span>
        <span className="text-2xs text-fg-subtle">{unit}</span>
        {note ? <span className="ml-auto text-2xs text-fg-subtle">{note}</span> : null}
      </figcaption>
      <div className="ae-chart relative min-w-0" style={{ minHeight: height }}>
        <div ref={host} className="w-full" aria-label={`${title} chart`} role="img" />
        {empty ? <div className="absolute inset-0 flex items-center justify-center text-2xs text-fg-subtle">Waiting for samples…</div> : null}
      </div>
    </figure>
  );
}
