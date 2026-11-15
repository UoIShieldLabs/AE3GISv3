// A tutorial's lab setup as the notebook shows it: whether its steps ran in the
// lab that is deployed now, how its background traffic is doing, and the
// actions behind "Configure lab" and the traffic switch. Nothing is kept in the
// browser: the state is read back from the runs the backend holds (found by
// their tag), so it survives a reload and a redeploy starts it over.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import * as api from '@/api/client';
import { useAppStore } from '@/store';
import { useAppShallow } from '@/store/selectors';
import { startPolling } from '@/features/deployment/statusPolling';
import type { Tutorial } from '@/types/topology';
import { toast } from '@/ui';
import { expandTraffic, rowOf, setupTag, stepsRequest, trafficTag, TRAFFIC_LABEL, type SetupNode } from './model';

const RUN_POLL_MS = 800;
const TRAFFIC_POLL_MS = 2000;
/** How long "starting"/"stopping" may wait for /runtime to agree. */
const PENDING_MS = 10000;

export type SetupState = 'unknown' | 'none' | 'running' | 'done' | 'failed';
export type TrafficState = 'off' | 'starting' | 'on' | 'stopping';

/** How a traffic row is doing while the traffic is on. */
export interface RowLive {
  running: number;
  total: number;
  /** A command that ended on its own: its exit code and last output. */
  ended?: { exit: number | null; output: string };
  /** What its commands printed last (the first that printed anything). */
  output?: string;
}

export interface LabSetupView {
  /** Why nothing can run right now (not deployed), or null. */
  blocked: string | null;
  setup: {
    state: SetupState;
    /** When the run started (ISO). */
    at: string | null;
    /** Results so far, by position among the runnable steps. */
    steps: api.ScenarioStepResult[];
  };
  traffic: {
    state: TrafficState;
    /** Per traffic row (by position); empty unless this tutorial's traffic runs. */
    rows: Record<number, RowLive>;
    /** Something else holds the background slot (another tutorial's traffic). */
    other: boolean;
  };
  configure: () => Promise<void>;
  setTraffic: (on: boolean) => Promise<void>;
}

const describe = (err: unknown) => (err instanceof Error ? err.message : String(err));

export function useLabSetup(tutorial: Tutorial, nodes: ReadonlyMap<string, SetupNode>): LabSetupView {
  const { backendId, deployed, deployedAt, activity } = useAppShallow((s) => ({
    backendId: s.backendId,
    deployed: s.deployStatus === 'deployed',
    deployedAt: s.deployedAt,
    activity: s.activity,
  }));
  const live = backendId && deployed ? backendId : null;
  const [run, setRun] = useState<api.ScenarioRun | null>(null);
  const [looked, setLooked] = useState(false);
  const [bgRun, setBgRun] = useState<api.BackgroundRun | null>(null);
  const [pending, setPending] = useState<'starting' | 'stopping' | null>(null);
  const alive = useRef(true);
  useEffect(() => { alive.current = true; return () => { alive.current = false; }; }, []);

  // ── Did the steps run in this lab? Find the tagged run newer than its deploy. ──
  const tag = setupTag(tutorial.id);
  useEffect(() => {
    setRun(null);
    setLooked(false);
    if (!live) return;
    let on = true;
    api.listScenarioRuns(live, 50)
      .then((runs) => {
        if (!on) return;
        const since = deployedAt ? Date.parse(deployedAt) : 0;
        setRun(runs.find((r) => r.tag === tag && Date.parse(r.job.created_at) >= since) ?? null);
        setLooked(true);
      })
      .catch(() => { if (on) setLooked(true); });
    return () => { on = false; };
  }, [live, deployedAt, tag]);

  // Follow it while it runs (the listing leaves the per-step results out).
  const runId = run?.id;
  const runLive = run?.live;
  const hasResults = !!run?.result?.steps;
  useEffect(() => {
    if (!runId || (!runLive && hasResults)) return;
    let on = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = async () => {
      const next = await api.getScenarioRun(runId).catch(() => null);
      if (!on) return;
      if (next) setRun(next);
      if (!next || next.live) timer = setTimeout(() => void tick(), RUN_POLL_MS);
    };
    void tick();
    return () => { on = false; if (timer) clearTimeout(timer); };
  }, [runId, runLive, hasResults]);

  // ── Background traffic: the background run and the iperf3 run, from /runtime. ──
  const bgJob = activity.find((a) => a.kind === 'background')?.job_id;
  const trafficJob = activity.find((a) => a.kind === 'traffic' && a.label.startsWith(TRAFFIC_LABEL))?.job_id;
  useEffect(() => {
    if (!bgJob) { setBgRun(null); return; }
    let on = true;
    let timer: ReturnType<typeof setTimeout> | null = null;
    const tick = async () => {
      const next = await api.getBackgroundRun(bgJob).catch(() => null);
      if (!on) return;
      if (next) setBgRun(next);
      timer = setTimeout(() => void tick(), TRAFFIC_POLL_MS);
    };
    void tick();
    return () => { on = false; if (timer) clearTimeout(timer); };
  }, [bgJob]);

  const isOn = !!bgJob || !!trafficJob;
  // "Starting"/"stopping" until /runtime agrees (or it clearly never will).
  useEffect(() => {
    if (!pending) return;
    if ((pending === 'starting') === isOn) { setPending(null); return; }
    const timer = setTimeout(() => setPending(null), PENDING_MS);
    return () => clearTimeout(timer);
  }, [pending, isOn]);

  const mine = !bgJob || bgRun?.tag === trafficTag(tutorial.id);
  const rows = useMemo(() => {
    const out: Record<number, RowLive> = {};
    if (!isOn || !mine) return out;
    for (const item of bgRun?.items ?? []) {
      const row = (out[rowOf(item.id)] ??= { running: 0, total: 0 });
      row.total += 1;
      if (item.status === 'running' || item.status === 'starting') row.running += 1;
      else if (item.status === 'exited' || item.status === 'error') row.ended ??= { exit: item.exit_code ?? null, output: item.output ?? '' };
      if (item.output) row.output ??= item.output;
    }
    if (trafficJob) {
      (tutorial.setup?.traffic ?? []).forEach((r, i) => { if (r.kind === 'iperf3') out[i] ??= { running: 1, total: 1 }; });
    }
    return out;
  }, [isOn, mine, bgRun, trafficJob, tutorial.setup]);

  const setTraffic = useCallback(async (on: boolean) => {
    const id = useAppStore.getState().backendId;
    if (!id) return;
    if (!on) {
      setPending('stopping');
      const jobs = useAppStore.getState().activity
        .filter((a) => a.kind === 'background' || (a.kind === 'traffic' && a.label.startsWith(TRAFFIC_LABEL)))
        .map((a) => a.job_id);
      await Promise.all(jobs.map((job) => api.stopJob(job).catch(() => null)));
      startPolling(id);
      return;
    }
    const { items, patterns, problems } = expandTraffic(tutorial.setup, nodes);
    if (!items.length && !patterns.length) {
      toast.error('No background traffic to start', { description: Object.values(problems)[0] });
      return;
    }
    setPending('starting');
    try {
      if (items.length) await api.startBackgroundRun(id, { items, label: TRAFFIC_LABEL, tag: trafficTag(tutorial.id) });
      if (patterns.length) await api.startTrafficRun(id, {
        patterns, flows: [], duration_s: null, interval_s: 1, ramp_s: 0, notes: '',
        label: `${TRAFFIC_LABEL}: ${tutorial.title}`.slice(0, 80),
      });
    } catch (err) {
      if (alive.current) setPending(null);
      const busy = err instanceof api.ApiError && (err.code === 'background_active' || err.code === 'traffic_active');
      toast.error(busy ? 'Traffic is already running on this lab' : "Couldn't start the background traffic", {
        description: busy ? 'Stop the running traffic first.' : describe(err),
      });
    }
    startPolling(id);
  }, [tutorial, nodes]);

  const configure = useCallback(async () => {
    const id = useAppStore.getState().backendId;
    if (!id) return;
    const request = stepsRequest(tutorial);
    if (request) {
      let started: api.ScenarioRun;
      try {
        started = await api.runScenarioSteps(id, request);
      } catch (err) {
        const busy = err instanceof api.ApiError && err.code === 'scenario_active';
        toast.error(busy ? 'Commands are already running on this lab' : "Couldn't run the lab setup", {
          description: busy ? 'Wait for them to finish, or stop them in the Scenario panel.' : describe(err),
        });
        return;
      }
      if (alive.current) { setRun(started); setLooked(true); }
      // Wait it out here too: the traffic starts only on a lab that is set up.
      let done = started;
      while (done.live) {
        await new Promise((resolve) => setTimeout(resolve, RUN_POLL_MS));
        done = await api.getScenarioRun(started.id).catch(() => done);
        if (!alive.current) return;
      }
      setRun(done);
      if (!succeeded(done)) return;
    }
    const st = useAppStore.getState();
    const trafficOn = st.activity.some((a) => a.kind === 'background' || (a.kind === 'traffic' && a.label.startsWith(TRAFFIC_LABEL)));
    if (tutorial.setup?.traffic?.length && !trafficOn) await setTraffic(true);
  }, [tutorial, setTraffic]);

  const setupState: SetupState = !live ? 'none' : run ? (run.live ? 'running' : succeeded(run) ? 'done' : 'failed') : looked ? 'none' : 'unknown';
  return {
    blocked: live ? null : 'Deploy the topology first',
    setup: { state: setupState, at: run?.job.started_at ?? run?.job.created_at ?? null, steps: (run?.result?.steps as api.ScenarioStepResult[] | undefined) ?? [] },
    traffic: { state: pending ?? (isOn ? 'on' : 'off'), rows, other: isOn && !mine },
    configure,
    setTraffic,
  };
}

/** Every step ran and exited 0. */
function succeeded(run: api.ScenarioRun): boolean {
  const result = run.result as { stopped_by?: string | null; failed?: number } | null | undefined;
  return run.status === 'succeeded' && result?.stopped_by === 'completed' && !result.failed;
}
