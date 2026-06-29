// Single source of truth for the persisted auth token.
// Persisted in localStorage under `piiga_token`. Subscribers (e.g. the
// AuthContext) are notified on change so state stays in sync across tabs.

const STORAGE_KEY = 'piiga_token';

type Listener = (token: string | null) => void;

const listeners = new Set<Listener>();

function read(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

let current: string | null = read();

export const tokenStore = {
  get(): string | null {
    return current;
  },

  set(token: string | null): void {
    current = token;
    try {
      if (token) {
        localStorage.setItem(STORAGE_KEY, token);
      } else {
        localStorage.removeItem(STORAGE_KEY);
      }
    } catch {
      /* storage unavailable (private mode) — keep in-memory value */
    }
    listeners.forEach((fn) => fn(token));
  },

  clear(): void {
    this.set(null);
  },

  subscribe(fn: Listener): () => void {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

export const TOKEN_STORAGE_KEY = STORAGE_KEY;
