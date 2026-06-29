import type { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';

/**
 * Gate for authenticated routes. Waits for the initial auth rehydrate
 * (isLoading) before deciding, then redirects unauthenticated users to /login
 * preserving the attempted location in router state.
 */
export function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return (
      <div
        role="status"
        aria-live="polite"
        style={{
          display: 'grid',
          placeItems: 'center',
          minHeight: '100dvh',
          color: 'var(--muted)',
        }}
      >
        Loading…
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }

  return <>{children}</>;
}
