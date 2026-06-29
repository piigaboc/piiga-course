// Typed fetch wrapper around the FastAPI backend.
//
// - Base URL from import.meta.env.VITE_API_BASE_URL (default '/api').
// - Attaches `Authorization: Bearer <token>` from the token store.
// - Parses JSON responses; throws a typed ApiError on non-2xx.
// - On 401: clears the token and dispatches a global `piiga:logout` event so
//   the AuthContext can redirect to /login.

import { tokenStore } from './tokenStore';

const BASE_URL: string =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? '/api';

/** Event dispatched on the window when the API sees a 401. */
export const LOGOUT_EVENT = 'piiga:logout';

export class ApiError extends Error {
  readonly status: number;
  readonly data: unknown;

  constructor(status: number, message: string, data: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

type Json = Record<string, unknown> | unknown[] | undefined;

interface RequestOptions {
  /** Skip attaching the Authorization header (e.g. login). */
  auth?: boolean;
  signal?: AbortSignal;
  headers?: Record<string, string>;
}

function buildUrl(path: string): string {
  if (path.startsWith('http')) return path;
  const base = BASE_URL.endsWith('/') ? BASE_URL.slice(0, -1) : BASE_URL;
  const suffix = path.startsWith('/') ? path : `/${path}`;
  return `${base}${suffix}`;
}

async function request<T>(
  method: string,
  path: string,
  body?: Json,
  options: RequestOptions = {},
): Promise<T> {
  const { auth = true, signal, headers = {} } = options;

  const finalHeaders: Record<string, string> = {
    Accept: 'application/json',
    ...headers,
  };

  if (body !== undefined) {
    finalHeaders['Content-Type'] = 'application/json';
  }

  if (auth) {
    const token = tokenStore.get();
    if (token) finalHeaders.Authorization = `Bearer ${token}`;
  }

  const res = await fetch(buildUrl(path), {
    method,
    headers: finalHeaders,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  });

  if (res.status === 401) {
    tokenStore.clear();
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(LOGOUT_EVENT));
    }
  }

  let data: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = text;
    }
  }

  if (!res.ok) {
    let detail: string | undefined;
    if (data && typeof data === 'object' && 'detail' in data) {
      const d = (data as { detail: unknown }).detail;
      if (typeof d === 'string') detail = d;
    }
    const message =
      detail ||
      res.statusText ||
      `Request failed with status ${res.status}`;
    throw new ApiError(res.status, message, data);
  }

  return data as T;
}

export const api = {
  get: <T>(path: string, options?: RequestOptions) =>
    request<T>('GET', path, undefined, options),
  post: <T>(path: string, body?: Json, options?: RequestOptions) =>
    request<T>('POST', path, body, options),
  patch: <T>(path: string, body?: Json, options?: RequestOptions) =>
    request<T>('PATCH', path, body, options),
  del: <T>(path: string, options?: RequestOptions) =>
    request<T>('DELETE', path, undefined, options),
};

// Convenience named exports.
export const get = api.get;
export const post = api.post;
export const patch = api.patch;
export const del = api.del;
