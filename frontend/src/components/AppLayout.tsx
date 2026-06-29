import type { ReactNode } from 'react';
import { NavLink, Outlet } from 'react-router-dom';
import { useAuth } from '../features/auth/AuthContext';
import { Button } from './Button';
import { Logo } from './Logo';
import {
  GridIcon,
  BooksIcon,
  CalendarIcon,
  SettingsIcon,
  UserIcon,
  LogOutIcon,
} from './icons';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
}

const NAV: NavItem[] = [
  { to: '/', label: 'Dashboard', icon: <GridIcon size={17} /> },
  { to: '/courses', label: 'Courses', icon: <BooksIcon size={17} /> },
  { to: '/calendar', label: 'Calendar', icon: <CalendarIcon size={17} /> },
  { to: '/settings', label: 'Settings', icon: <SettingsIcon size={17} /> },
];

function navClass({ isActive }: { isActive: boolean }): string {
  return isActive ? 'navlink navlink--active' : 'navlink';
}

/**
 * Shared chrome for authenticated pages: stone sidebar nav (with inline icons
 * and a green active indicator) + topbar with the current user email in mono
 * and a logout button. Renders the active route via <Outlet>.
 */
export function AppLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="layout">
      <aside className="layout__sidebar">
        <div className="layout__brand">
          <Logo size={22} withWordmark />
        </div>
        <nav className="layout__nav" aria-label="Primary">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={navClass}
            >
              <span className="navlink__icon" aria-hidden="true">
                {item.icon}
              </span>
              <span className="navlink__label">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="layout__main">
        <header className="layout__topbar">
          <div />
          <div className="layout__user">
            {user && (
              <span className="layout__user-email mono" title={user.email}>
                <UserIcon size={15} />
                {user.email}
              </span>
            )}
            <Button variant="outline" size="sm" onClick={logout}>
              <LogOutIcon />
              Log out
            </Button>
          </div>
        </header>
        <main className="layout__content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
