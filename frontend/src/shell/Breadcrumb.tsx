import { ChevronRight, Globe } from 'lucide-react';
import { cn } from '@/lib/cn';
import type { Scope } from '@/lib/topology';
import { useAppStore } from '@/store';

export interface BreadcrumbProps {
  scope: Scope;
  onNavigate: (scope: Scope) => void;
  className?: string;
}

/** Network › Site › Subnet path for the current scope. */
export function Breadcrumb({ scope, onNavigate, className }: BreadcrumbProps) {
  const topology = useAppStore((s) => s.topology);
  const site = scope.level !== 'root' ? topology.sites.find((s) => s.id === scope.siteId) : undefined;
  const subnet = scope.level === 'subnet' ? site?.subnets.find((s) => s.id === scope.subnetId) : undefined;

  const crumbs: { label: React.ReactNode; scope: Scope; current: boolean }[] = [
    { label: <span className="flex items-center gap-1.5"><Globe className="size-3.5" /> Network</span>, scope: { level: 'root' }, current: scope.level === 'root' },
  ];
  if (site) crumbs.push({ label: site.name, scope: { level: 'site', siteId: site.id }, current: scope.level === 'site' });
  if (site && subnet) crumbs.push({ label: <>{subnet.name} <span className="ml-1 font-mono text-2xs text-fg-subtle">{subnet.cidr}</span></>, scope: { level: 'subnet', siteId: site.id, subnetId: subnet.id }, current: true });

  return (
    <nav aria-label="Scope" className={cn('flex min-w-0 items-center gap-0.5 text-[13px]', className)}>
      {crumbs.map((c, i) => (
        <span key={i} className="flex min-w-0 items-center gap-0.5">
          {i > 0 ? <ChevronRight className="size-3.5 shrink-0 text-fg-subtle" /> : null}
          <button
            type="button"
            onClick={() => onNavigate(c.scope)}
            aria-current={c.current ? 'page' : undefined}
            className={cn(
              'truncate rounded-md px-1.5 py-0.5 transition-colors',
              c.current ? 'font-medium text-fg' : 'text-fg-muted hover:bg-hover hover:text-fg',
            )}
          >
            {c.label}
          </button>
        </span>
      ))}
    </nav>
  );
}
