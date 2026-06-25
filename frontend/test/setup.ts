import '@testing-library/jest-dom/vitest';
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';

afterEach(() => {
  cleanup();
});

// jsdom's `window.localStorage` is unreliable across Node versions (under Node 25 it resolves
// to an object with no methods — likely jsdom racing Node's own experimental global Storage).
// No test used localStorage before U10's dark-mode toggle, so this never surfaced until now.
// A minimal in-memory Storage polyfill keeps tests deterministic regardless of the host's
// jsdom/Node combination.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  clear(): void {
    this.store.clear();
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number): string | null {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }
}

if (typeof window.localStorage?.setItem !== 'function') {
  Object.defineProperty(window, 'localStorage', { value: new MemoryStorage() });
}
