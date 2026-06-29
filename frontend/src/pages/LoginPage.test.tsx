import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { LoginPage } from './LoginPage';
import { ApiError } from '../lib/api';

const login = vi.fn();
const verifyMfa = vi.fn();
const navigate = vi.fn();

vi.mock('../features/auth/AuthContext', () => ({
  useAuth: () => ({ login, verifyMfa }),
}));

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>(
    'react-router-dom',
  );
  return {
    ...actual,
    useNavigate: () => navigate,
  };
});

function renderLogin() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe('LoginPage', () => {
  afterEach(() => {
    login.mockReset();
    verifyMfa.mockReset();
    navigate.mockReset();
  });

  it('logs in directly when MFA is not required', async () => {
    login.mockResolvedValue({ mfa_required: false });
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    await waitFor(() => expect(login).toHaveBeenCalledWith('a@b.com', 'pw'));
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('switches to the MFA step and verifies the code', async () => {
    login.mockResolvedValue({ mfa_required: true, mfa_token: 'mtok' });
    verifyMfa.mockResolvedValue(undefined);
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'pw');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    // Second step appears.
    const codeInput = await screen.findByLabelText('Authentication code');
    expect(navigate).not.toHaveBeenCalled();

    await userEvent.type(codeInput, '123456');
    await userEvent.click(screen.getByRole('button', { name: /verify/i }));

    await waitFor(() =>
      expect(verifyMfa).toHaveBeenCalledWith('mtok', '123456'),
    );
    expect(navigate).toHaveBeenCalledWith('/', { replace: true });
  });

  it('shows the ApiError message on failed login', async () => {
    login.mockRejectedValue(new ApiError(401, 'Invalid credentials', null));
    renderLogin();

    await userEvent.type(screen.getByLabelText('Email'), 'a@b.com');
    await userEvent.type(screen.getByLabelText('Password'), 'bad');
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }));

    expect(await screen.findByText('Invalid credentials')).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
  });
});
