import { useEffect, useState } from 'react';
import * as api from '@/api/client';
import { useAppShallow } from '@/store/selectors';
import { useAgentStore } from './agentStore';

const REFRESH_MS = 15_000;

/** Whose chats the panel can also show: the open topology's owner, when that's
 *  someone else (staff on a student's topology, an admin on anyone's). */
export function useOwnerTarget(): { ownerId: string; username: string; topologyId: string } | null {
  const { owner, meId, topologyId } = useAppShallow((s) => ({
    owner: s.owner,
    meId: s.user?.id ?? null,
    topologyId: s.backendId,
  }));
  const agentOn = useAgentStore((s) => !!s.status?.enabled);
  if (!agentOn || !owner || !topologyId || !meId || owner.id === meId) return null;
  return { ownerId: owner.id, username: owner.username, topologyId };
}

/** That owner's chats on the open topology (null: none to show, or still loading). */
export function useOwnerChats(): { username: string; chats: api.AgentChat[] } | null {
  const target = useOwnerTarget();
  const loaded = useAgentStore((s) => s.ownerChats);
  if (!target || !loaded || loaded.key !== `${target.ownerId}:${target.topologyId}`) return null;
  return { username: target.username, chats: loaded.chats };
}

/** Keeps `ownerChats` fresh while mounted (the open panel). */
export function useOwnerChatsLoader(): void {
  const target = useOwnerTarget();
  const ownerId = target?.ownerId;
  const topologyId = target?.topologyId;

  useEffect(() => {
    if (!ownerId || !topologyId) return;
    const key = `${ownerId}:${topologyId}`;
    let live = true;
    const load = () =>
      api
        .listAgentChats({ owner: ownerId, topologyId })
        .then((chats) => live && useAgentStore.getState().setOwnerChats({ key, chats }))
        .catch(() => undefined);
    void load();
    const timer = window.setInterval(() => void load(), REFRESH_MS);
    return () => {
      live = false;
      window.clearInterval(timer);
    };
  }, [ownerId, topologyId]);
}

/** How many chats a user (a student, for their instructor) has on each of their
 *  topologies, by topology id. Empty until loaded, or with no owner. */
export function useChatCounts(ownerId: string | null): Map<string, number> {
  const agentOn = useAgentStore((s) => !!s.status?.enabled);
  const [counts, setCounts] = useState<{ ownerId: string; counts: Map<string, number> } | null>(null);

  useEffect(() => {
    if (!agentOn || !ownerId) return;
    let live = true;
    api
      .listAgentChats({ owner: ownerId })
      .then((chats) => {
        if (!live) return;
        const m = new Map<string, number>();
        for (const c of chats) if (c.topology_id) m.set(c.topology_id, (m.get(c.topology_id) ?? 0) + 1);
        setCounts({ ownerId, counts: m });
      })
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [agentOn, ownerId]);

  return counts && counts.ownerId === ownerId ? counts.counts : EMPTY;
}

const EMPTY = new Map<string, number>();
