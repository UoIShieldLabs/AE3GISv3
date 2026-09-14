import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';
import { useAppStore } from '@/store';
import { cn } from '@/lib/cn';
import { Section } from './Section';

/** Backend diagnostics for the current design. Errors block deployment. */
export function IssuesSection() {
  const diagnostics = useAppStore((s) => s.diagnostics);
  const selectNodes = useAppStore((s) => s.selectNodes);
  const errors = diagnostics.filter((d) => d.severity === 'error');
  const warnings = diagnostics.filter((d) => d.severity === 'warning');
  const title = diagnostics.length ? `Issues (${errors.length} error${errors.length === 1 ? '' : 's'}, ${warnings.length} warning${warnings.length === 1 ? '' : 's'})` : 'Issues';

  return (
    <Section title={title} defaultOpen={errors.length > 0}>
      {diagnostics.length === 0 ? (
        <p className="flex items-center gap-1.5 text-xs text-success"><CheckCircle2 className="size-3.5" /> No issues reported by the backend.</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {[...errors, ...warnings].map((d, i) => (
            <li key={`${d.code}-${d.path}-${i}`}>
              <button
                type="button"
                onClick={() => { if (d.node_id) selectNodes([d.node_id]); }}
                className={cn(
                  'flex w-full items-start gap-2 rounded-md px-2 py-1.5 text-left text-xs',
                  d.node_id ? 'hover:bg-hover' : 'cursor-default',
                )}
              >
                {d.severity === 'error' ? <AlertTriangle className="mt-0.5 size-3.5 shrink-0 text-danger" /> : <Info className="mt-0.5 size-3.5 shrink-0 text-warning" />}
                <span className="min-w-0">
                  <span className="block">{d.message}</span>
                  <span className="block truncate font-mono text-2xs text-fg-subtle">{d.code}{d.path ? ` · ${d.path}` : ''}</span>
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}
