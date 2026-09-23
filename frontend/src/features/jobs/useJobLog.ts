// Following a job's log (GET /jobs/{id}/log) by byte offset. The first read
// takes the tail, so a long build log opens at its end rather than its start.
import { useEffect, useState } from 'react';
import * as api from '@/api/client';

export const MAX_LINES = 5000;

export interface LogState {
  lines: string[];
  offset: number;
  done: boolean;
  /** Bytes before the first line we fetched (the log's older part). */
  skippedBytes: number;
  /** Lines dropped from the front to stay under MAX_LINES. */
  droppedLines: number;
}

export const EMPTY_LOG: LogState = { lines: [], offset: 0, done: false, skippedBytes: 0, droppedLines: 0 };

/** Fold one chunk into the state (pure). */
export function appendChunk(state: LogState, chunk: Pick<api.JobLog, 'text' | 'next_offset' | 'done'>, maxLines = MAX_LINES): LogState {
  const incoming = chunk.text ? chunk.text.replace(/\n$/, '').split('\n') : [];
  let lines = incoming.length ? [...state.lines, ...incoming] : state.lines;
  let droppedLines = state.droppedLines;
  if (lines.length > maxLines) {
    droppedLines += lines.length - maxLines;
    lines = lines.slice(-maxLines);
  }
  return { ...state, lines, offset: chunk.next_offset, done: chunk.done, droppedLines };
}

/** Follow a job's log until the job is done (null: nothing to follow). */
export function useJobLog(jobId: string | null | undefined): LogState {
  const [state, setState] = useState<{ jobId: string | null; log: LogState }>({ jobId: null, log: EMPTY_LOG });

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let log = EMPTY_LOG;

    const tick = async (first: boolean) => {
      try {
        const chunk = await api.getJobLog(jobId, first ? undefined : log.offset);
        if (cancelled) return;
        log = appendChunk(first ? { ...EMPTY_LOG, skippedBytes: chunk.offset } : log, chunk);
        setState({ jobId, log });
        if (chunk.done) return;
        // Drain a backlog quickly; otherwise poll.
        timer = setTimeout(() => void tick(false), chunk.next_offset < chunk.size ? 50 : 1000);
      } catch {
        if (!cancelled) timer = setTimeout(() => void tick(first), 3000);
      }
    };
    void tick(true);
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [jobId]);

  return state.jobId === jobId ? state.log : EMPTY_LOG;
}
