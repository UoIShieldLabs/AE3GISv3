import { describe, it, expect } from 'vitest';
import { isValidIp, isValidCidr, parseCidr, isIpInCidr, getNextAvailableIp, getSubnetCapacity } from '../validation';

describe('IP/CIDR validation', () => {
  it('validates IPv4 addresses', () => {
    expect(isValidIp('10.0.0.1')).toBe(true);
    expect(isValidIp('255.255.255.255')).toBe(true);
    expect(isValidIp('256.0.0.1')).toBe(false);
    expect(isValidIp('10.0.0')).toBe(false);
    expect(isValidIp('01.2.3.4')).toBe(false); // no leading zeros
  });

  it('validates CIDRs', () => {
    expect(isValidCidr('10.0.1.0/24')).toBe(true);
    expect(isValidCidr('10.0.1.0/33')).toBe(false);
    expect(isValidCidr('10.0.1.0')).toBe(false);
  });

  it('parses a /24', () => {
    const info = parseCidr('10.0.1.0/24')!;
    expect(info.prefix).toBe(24);
    expect(getSubnetCapacity('10.0.1.0/24')).toBe(254);
  });

  it('checks host membership', () => {
    expect(isIpInCidr('10.0.1.5', '10.0.1.0/24')).toBe(true);
    expect(isIpInCidr('10.0.2.5', '10.0.1.0/24')).toBe(false);
  });

  it('finds the next available IP skipping taken ones', () => {
    expect(getNextAvailableIp('10.0.1.0/24', [])).toBe('10.0.1.1');
    expect(getNextAvailableIp('10.0.1.0/24', ['10.0.1.1', '10.0.1.2'])).toBe('10.0.1.3');
  });
});
