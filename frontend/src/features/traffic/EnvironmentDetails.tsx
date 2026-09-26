import { useEffect, useState } from 'react';
import * as api from '@/api/client';
import { formatBytes } from '@/features/capture/packetBuffer';

/** The parts of run.json's environment this view shows (see backend domain/environment.py). */
interface RunEnvironment {
  fingerprint?: string;
  host?: { label?: string | null };
  ae3gis?: { git_commit?: string | null; git_dirty?: boolean; mode?: string | null };
  engine?: {
    docker?: { os?: string; arch?: string; ncpu?: number; mem_total?: number; kernel?: string; server_version?: string; cgroup_version?: string };
    kathara?: { version?: string | null; network_plugin?: { name?: string } };
  };
  tool?: { versions?: Record<string, string> };
}

function useRunEnvironment(jobId: string): RunEnvironment | null {
  const [env, setEnv] = useState<RunEnvironment | null>(null);
  useEffect(() => {
    let live = true;
    api.getArtifactJson<{ environment?: RunEnvironment }>(jobId, 'run.json')
      .then((d) => { if (live) setEnv(d.environment ?? {}); })
      .catch(() => { if (live) setEnv({}); });
    return () => { live = false; };
  }, [jobId]);
  return env;
}

function Body({ jobId, fingerprint }: { jobId: string; fingerprint?: string }) {
  const e = useRunEnvironment(jobId);
  if (!e) return <div className="mt-1">Loading…</div>;
  const docker = e.engine?.docker ?? {};
  const kathara = e.engine?.kathara ?? {};
  const rows: [string, string][] = [
    ['Host', `${e.host?.label || 'unnamed (set AE3GIS_HOST_LABEL)'} · ${docker.os ?? '?'} · ${docker.arch ?? '?'} · ${docker.ncpu ?? '?'} CPUs · ${formatBytes(docker.mem_total)}`],
    ['Kernel / Docker', `${docker.kernel ?? '?'} · Docker ${docker.server_version ?? '?'} · cgroup v${docker.cgroup_version ?? '?'}`],
    ['Kathará', `${kathara.version ?? '?'} · ${kathara.network_plugin?.name ?? '?'}`],
    ['AE3GIS', `${e.ae3gis?.git_commit?.slice(0, 12) ?? 'unknown commit'}${e.ae3gis?.git_dirty ? ' (modified)' : ''}${e.ae3gis?.mode ? ` · ${e.ae3gis.mode}` : ''}`],
    ['Tools', Object.values(e.tool?.versions ?? {}).join(' · ') || '–'],
    ['Fingerprint', fingerprint ?? e.fingerprint ?? '–'],
  ];
  return (
    <dl className="mt-1.5 grid grid-cols-[8rem_1fr] gap-x-3 gap-y-1">
      {rows.map(([k, v]) => (
        <div key={k} className="contents">
          <dt>{k}</dt>
          <dd className="break-all font-mono text-fg">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Where a run happened (host, versions, images): what makes results comparable. */
export function EnvironmentDetails({ jobId, fingerprint }: { jobId: string; fingerprint?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <details className="mt-5 text-2xs text-fg-muted" onToggle={(e) => setOpen((e.target as HTMLDetailsElement).open)}>
      <summary className="cursor-pointer select-none font-medium text-fg">Environment</summary>
      {open ? <Body jobId={jobId} fingerprint={fingerprint} /> : null}
    </details>
  );
}
