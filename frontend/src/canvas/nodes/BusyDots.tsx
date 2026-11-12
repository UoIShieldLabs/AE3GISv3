const MAX_BUSY_DOTS = 5;

/** A collapsed subnet or site card: one dot per device inside with something
 *  running, in that device's colour (the live lab view). */
export function BusyDots({ colors }: { colors: string[] }) {
  const shown = colors.slice(0, MAX_BUSY_DOTS);
  return (
    <span className="ae-node-busy flex shrink-0 items-center gap-0.5" aria-label={`${colors.length} device${colors.length === 1 ? '' : 's'} with something running`} title={`${colors.length} device${colors.length === 1 ? '' : 's'} with something running`}>
      {shown.map((color, i) => <span key={i} className="size-1.5 rounded-full" style={{ backgroundColor: color }} />)}
      {colors.length > shown.length ? <span className="text-2xs text-fg-muted">+{colors.length - shown.length}</span> : null}
    </span>
  );
}
