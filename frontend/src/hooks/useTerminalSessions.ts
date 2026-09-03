import { useCallback, useState } from 'react';
import type { Container } from '../types/topology';

/** Manage the set of open interactive-terminal tabs. */
export function useTerminalSessions() {
  const [sessions, setSessions] = useState<Container[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [minimized, setMinimized] = useState(false);

  const open = useCallback((container: Container) => {
    setSessions((prev) => (prev.find((c) => c.id === container.id) ? prev : [...prev, container]));
    setActiveId(container.id);
    setMinimized(false);
  }, []);

  const close = useCallback((id: string) => {
    setSessions((prev) => {
      const next = prev.filter((c) => c.id !== id);
      setActiveId((curr) => (curr === id ? (next.length ? next[next.length - 1].id : null) : curr));
      return next;
    });
  }, []);

  return { sessions, activeId, minimized, setActiveId, setMinimized, open, close };
}
