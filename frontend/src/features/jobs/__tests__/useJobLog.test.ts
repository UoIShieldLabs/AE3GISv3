import { describe, expect, it } from 'vitest';
import { appendChunk, EMPTY_LOG } from '../useJobLog';

describe('appendChunk', () => {
  it('splits lines and advances the offset', () => {
    const a = appendChunk(EMPTY_LOG, { text: 'one\ntwo\n', next_offset: 8, done: false });
    expect(a.lines).toEqual(['one', 'two']);
    expect(a.offset).toBe(8);
    const b = appendChunk(a, { text: '', next_offset: 8, done: true });
    expect(b.lines).toBe(a.lines);
    expect(b.done).toBe(true);
  });

  it('keeps only the newest lines past the cap', () => {
    let s = EMPTY_LOG;
    s = appendChunk(s, { text: 'a\nb\nc\n', next_offset: 6, done: false }, 4);
    s = appendChunk(s, { text: 'd\ne\n', next_offset: 10, done: false }, 4);
    expect(s.lines).toEqual(['b', 'c', 'd', 'e']);
    expect(s.droppedLines).toBe(1);
  });
});
