import { useEffect, useState } from 'react';

const GLYPHS = '01!#$%&*+-<>?@[]^_{}|~ABCDEFabcdef';

const reducedMotion = () => !!window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;

/** Swap every character but separators for a random glyph. */
function scramble(rest: string): string {
  return rest.replace(/[^\s.:/-]/g, () => GLYPHS[Math.floor(Math.random() * GLYPHS.length)]);
}

/** `text`, revealed left to right out of random glyphs over `duration` ms each
 *  time `active` turns on (a theme effect). Plain `text` otherwise, and with
 *  reduced motion. Only the node using it re-renders while it runs. */
export function useDecrypt(text: string, active: boolean, duration = 400): string {
  const [frame, setFrame] = useState<string | null>(null);
  useEffect(() => {
    if (!active || reducedMotion()) return;
    let raf = 0;
    const start = performance.now();
    const step = (now: number) => {
      const p = (now - start) / duration;
      if (p >= 1) {
        setFrame(null);
        return;
      }
      const settled = Math.floor(Math.max(0, p) * text.length);
      setFrame(text.slice(0, settled) + scramble(text.slice(settled)));
      raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => {
      cancelAnimationFrame(raf);
      setFrame(null);
    };
  }, [text, active, duration]);
  return active && frame !== null ? frame : text;
}
