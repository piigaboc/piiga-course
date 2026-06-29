import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError, LOGOUT_EVENT } from './api';
import { tokenStore } from './tokenStore';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(body == null ? '' : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

describe('api', () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => {
    tokenStore.clear();
  });

  it('attaches the bearer token when present', async () => {
    tokenStore.set('abc123');
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ ok: true }));

    await api.get('/stats');

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBe('Bearer abc123');
  });

  it('omits auth header when auth:false', async () => {
    tokenStore.set('abc123');
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue(jsonResponse({ ok: true }));

    await api.post('/auth/login', { email: 'x' }, { auth: false });

    const [, init] = fetchMock.mock.calls[0];
    const headers = init?.headers as Record<string, string>;
    expect(headers.Authorization).toBeUndefined();
  });

  it('throws a typed ApiError with the backend detail on non-2xx', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(
      jsonResponse({ detail: 'Bad credentials' }, 400),
    );

    await expect(api.post('/auth/login', {}, { auth: false })).rejects.toMatchObject({
      name: 'ApiError',
      status: 400,
      message: 'Bad credentials',
    });
  });

  it('clears the token and dispatches logout on 401', async () => {
    tokenStore.set('expired');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(null, 401));
    const onLogout = vi.fn();
    window.addEventListener(LOGOUT_EVENT, onLogout);

    await expect(api.get('/auth/me')).rejects.toBeInstanceOf(ApiError);
    expect(tokenStore.get()).toBeNull();
    expect(onLogout).toHaveBeenCalledTimes(1);

    window.removeEventListener(LOGOUT_EVENT, onLogout);
  });
});
