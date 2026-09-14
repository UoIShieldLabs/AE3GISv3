/** Short, URL-safe unique ids for topology entities (sites, subnets, containers, connections). */
export function generateId(prefix?: string): string {
  const id =
    typeof crypto !== 'undefined' && 'randomUUID' in crypto
      ? crypto.randomUUID().replace(/-/g, '').slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return prefix ? `${prefix}-${id}` : id;
}
