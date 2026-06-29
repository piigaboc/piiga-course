import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { AuthProvider, useAuth } from './AuthContext';
import { tokenStore } from '../../lib/tokenStore';

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(body == null ? '' : JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}

const USER = {
  id: 'u1',
  email: 'a@b.com',
  display_name: 'A B',
  totp_enabled: false,
};

function Harness() {
  const { user, isAuthenticated, isLoading, login } = useAuth();
  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="auth">{String(isAuthenticated)}</span>
      <span data-testid="email">{user?.email ?? ''}</span>
      <button onClick={() => void login('a@b.com', 'pw')}>login</button>
    </div>
  );
}

describe('AuthContext', () => {
  beforeEach(() => {
    tokenStore.clear();
    vi.restoreAllMocks();
  });
  afterEach(() => tokenStore.clear());

  it('starts unauthenticated with no token', async () => {
    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );
    expect(screen.getByTestId('auth')).toHaveTextContent('false');
  });

  it('logs in without MFA: stores token and loads the user', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith('/auth/login')) {
        return Promise.resolve(
          jsonResponse({ mfa_required: false, access_token: 'tok', token_type: 'bearer' }),
        );
      }
      if (url.endsWith('/auth/me')) {
        return Promise.resolve(jsonResponse(USER));
      }
      return Promise.reject(new Error(`unexpected ${url}`));
    });

    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    );
    await waitFor(() =>
      expect(screen.getByTestId('loading')).toHaveTextContent('false'),
    );

    await userEvent.click(screen.getByRole('button', { name: 'login' }));

    await waitFor(() =>
      expect(screen.getByTestId('email')).toHaveTextContent('a@b.com'),
    );
    expect(screen.getByTestId('auth')).toHaveTextContent('true');
    expect(tokenStore.get()).toBe('tok');
    expect(fetchMock).toHaveBeenCalled();
  });

  it('rehydrates the user from a persisted token on mount', async () => {
    tokenStore.set('persisted');
    vi.spyOn(globalThis, 'fetch').mockResolvedValue(jsonResponse(USER));

    render(
      <AuthProvider>
        <Harness />
      </AuthProvider>,
    );

    await waitFor(() =>
      expect(screen.getByTestId('email')).toHaveTextContent('a@b.com'),
    );
    expect(screen.getByTestId('auth')).toHaveTextContent('true');
  });
});
