import { planNodeFor, usePlan } from '@/features/deployment/usePlan';
import { Section } from './Section';

/** What the backend will actually instantiate for this device (from the saved design). */
export function DeploymentSection({ nodeId }: { nodeId: string }) {
  const { plan, loading, stale } = usePlan();
  const node = planNodeFor(plan, nodeId);
  return (
    <Section title="Deployment plan" defaultOpen={false}>
      {!plan && loading ? <p className="text-2xs text-fg-subtle">Loading plan…</p> : null}
      {!plan && !loading ? <p className="text-2xs text-fg-subtle">Save the topology to see the computed plan.</p> : null}
      {plan && !node ? <p className="text-2xs text-fg-subtle">Not part of the saved design yet — save to include it.</p> : null}
      {node ? (
        <div className="flex flex-col gap-2 text-xs">
          {stale ? <p className="rounded-md bg-warning-soft px-2 py-1 text-2xs text-warning">Shows the last saved version; save to refresh.</p> : null}
          <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
            <span className="text-fg-muted">Machine</span><span className="font-mono">{node.machine_name}</span>
            <span className="text-fg-muted">Role</span><span>{node.role}</span>
            <span className="text-fg-muted">Image</span><span className="truncate font-mono">{node.image}</span>
          </div>
          <div>
            <div className="mb-1 text-2xs font-semibold uppercase tracking-wide text-fg-subtle">Interfaces</div>
            {node.interfaces.length === 0 ? <p className="text-2xs text-fg-subtle">No links, so no interfaces.</p> : (
              <table className="w-full font-mono text-2xs">
                <tbody>
                  {node.interfaces.map((i) => (
                    <tr key={i.name} className="border-t border-border">
                      <td className="py-0.5 pr-2">{i.name}</td>
                      <td className="py-0.5 pr-2 text-fg-muted">{i.collision_domain}</td>
                      <td className="py-0.5 text-right">{i.ip ? `${i.ip}/${i.prefix_len}` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
          <div>
            <div className="mb-1 text-2xs font-semibold uppercase tracking-wide text-fg-subtle">Boot commands</div>
            {node.startup.length === 0 ? <p className="text-2xs text-fg-subtle">None.</p> : (
              <pre className="max-h-48 overflow-auto rounded-md bg-surface-2 p-2 font-mono text-2xs leading-relaxed">{node.startup.join('\n')}</pre>
            )}
          </div>
        </div>
      ) : null}
    </Section>
  );
}
