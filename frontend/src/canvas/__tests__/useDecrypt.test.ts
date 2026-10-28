import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useDecrypt } from '../nodes/useDecrypt';
import { nodeCardClass } from '../nodes/nodeStyles';

beforeEach(() => vi.useFakeTimers({ toFake: ['requestAnimationFrame', 'cancelAnimationFrame', 'performance'] }));
afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

describe('useDecrypt', () => {
  it('leaves the text alone while inactive', () => {
    const { result } = renderHook(() => useDecrypt('web-01', false));
    act(() => { vi.advanceTimersByTime(100); });
    expect(result.current).toBe('web-01');
  });

  it('scrambles, keeps separators, then settles on the exact text', () => {
    const { result } = renderHook(() => useDecrypt('10.0.3.30', true, 400));
    act(() => { vi.advanceTimersByTime(40); });
    expect(result.current).toHaveLength('10.0.3.30'.length);
    expect(result.current.replace(/[^.]/g, '')).toBe('...');
    act(() => { vi.advanceTimersByTime(500); });
    expect(result.current).toBe('10.0.3.30');
  });

  it('does nothing with reduced motion', () => {
    vi.stubGlobal('matchMedia', (q: string) => ({ matches: q.includes('reduce') }));
    const { result } = renderHook(() => useDecrypt('web-01', true));
    act(() => { vi.advanceTimersByTime(100); });
    expect(result.current).toBe('web-01');
  });
});

describe('node cards', () => {
  it('carry the ae-node theme hook', () => {
    expect(nodeCardClass(false).split(' ')).toContain('ae-node');
    expect(nodeCardClass(true).split(' ')).toContain('ae-node');
  });
});
