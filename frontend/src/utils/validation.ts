export function isValidIp(value: string): boolean {
  const parts = value.split('.');
  if (parts.length !== 4) return false;
  return parts.every(p => {
    const n = Number(p);
    return Number.isInteger(n) && n >= 0 && n <= 255 && p === String(n);
  });
}

export function isValidCidr(value: string): boolean {
  const [ip, prefix] = value.split('/');
  if (!ip || !prefix) return false;
  if (!isValidIp(ip)) return false;
  const n = Number(prefix);
  return Number.isInteger(n) && n >= 0 && n <= 32 && prefix === String(n);
}

// ── IP ↔ number helpers ──

export function ipToNumber(ip: string): number {
  const parts = ip.split('.').map(Number);
  return ((parts[0] << 24) | (parts[1] << 16) | (parts[2] << 8) | parts[3]) >>> 0;
}

export function numberToIp(n: number): string {
  return [
    (n >>> 24) & 0xff,
    (n >>> 16) & 0xff,
    (n >>> 8) & 0xff,
    n & 0xff,
  ].join('.');
}

// ── CIDR helpers ──

export interface CidrInfo {
  networkAddr: number;   // network address (e.g. 10.0.1.0)
  broadcastAddr: number; // broadcast address (e.g. 10.0.1.255)
  firstHost: number;     // first usable host (.1)
  lastHost: number;      // last usable host (.254)
  prefix: number;
}

export function parseCidr(cidr: string): CidrInfo | null {
  if (!isValidCidr(cidr)) return null;
  const [ip, prefixStr] = cidr.split('/');
  const prefix = Number(prefixStr);
  const mask = prefix === 0 ? 0 : (~0 << (32 - prefix)) >>> 0;
  const networkAddr = (ipToNumber(ip) & mask) >>> 0;
  const broadcastAddr = (networkAddr | ~mask) >>> 0;
  return {
    networkAddr,
    broadcastAddr,
    firstHost: (networkAddr + 1) >>> 0,
    lastHost: (broadcastAddr - 1) >>> 0,
    prefix,
  };
}

/** Check if an IP string falls within a CIDR range (host portion only). */
export function isIpInCidr(ip: string, cidr: string): boolean {
  const info = parseCidr(cidr);
  if (!info || !isValidIp(ip)) return false;
  const n = ipToNumber(ip);
  return n >= info.firstHost && n <= info.lastHost;
}

/**
 * Find the next available IP in a CIDR range, skipping taken IPs.
 * Returns null if the subnet is full.
 */
export function getNextAvailableIp(cidr: string, takenIps: string[]): string | null {
  const info = parseCidr(cidr);
  if (!info) return null;

  const taken = new Set(takenIps.map(ip => ipToNumber(ip)));

  for (let addr = info.firstHost; addr <= info.lastHost; addr++) {
    if (!taken.has(addr >>> 0)) {
      return numberToIp(addr >>> 0);
    }
  }
  return null; // subnet full
}

/** Total usable host count for a CIDR (excludes network + broadcast). */
export function getSubnetCapacity(cidr: string): number {
  const info = parseCidr(cidr);
  if (!info) return 0;
  return (info.lastHost - info.firstHost + 1) >>> 0;
}

/**
 * Find N consecutive-ish available IPs starting from a given offset in the CIDR.
 * Returns as many as available (may be fewer than requested).
 */
export function getAvailableIps(cidr: string, takenIps: string[], count: number): string[] {
  const info = parseCidr(cidr);
  if (!info) return [];

  const taken = new Set(takenIps.map(ip => ipToNumber(ip)));
  const result: string[] = [];

  for (let addr = info.firstHost; addr <= info.lastHost && result.length < count; addr++) {
    const a = addr >>> 0;
    if (!taken.has(a)) {
      result.push(numberToIp(a));
      taken.add(a); // mark as taken so subsequent calls don't overlap
    }
  }
  return result;
}
