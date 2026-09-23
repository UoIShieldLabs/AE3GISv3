// Vitest setup: DOM matchers + the browser APIs React Flow needs under jsdom.
import '@testing-library/jest-dom/vitest';

class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}

if (!('ResizeObserver' in globalThis)) {
  Object.defineProperty(globalThis, 'ResizeObserver', { writable: true, value: ResizeObserverMock });
}

class DOMMatrixReadOnlyMock {
  m22: number;
  constructor(transform?: string) {
    const scale = transform?.match(/scale\(([1-9.])\)/)?.[1];
    this.m22 = scale !== undefined ? +scale : 1;
  }
}

if (!('DOMMatrixReadOnly' in globalThis)) {
  Object.defineProperty(globalThis, 'DOMMatrixReadOnly', { writable: true, value: DOMMatrixReadOnlyMock });
}

Object.defineProperties(globalThis.HTMLElement.prototype, {
  offsetHeight: { configurable: true, get() { return parseFloat(this.style.height) || 1; } },
  offsetWidth: { configurable: true, get() { return parseFloat(this.style.width) || 1; } },
});

(globalThis.SVGElement.prototype as unknown as { getBBox: () => DOMRect }).getBBox = () =>
  ({ x: 0, y: 0, width: 0, height: 0 } as DOMRect);

if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

// cmdk (Combobox, command palette) scrolls the highlighted item into view.
if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = function scrollIntoView() {};
}
