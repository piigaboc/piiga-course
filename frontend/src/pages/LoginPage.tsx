import { useState, type FormEvent } from 'react';
import { useLocation, useNavigate, type Location } from 'react-router-dom';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Logo } from '../components/Logo';
import { useAuth } from '../features/auth/AuthContext';
import { ApiError } from '../lib/api';
import './login.css';

type Step = 'credentials' | 'mfa';

interface FromState {
  from?: Location;
}

/**
 * Minimal login + MFA flow. This is intentionally lightweight for the
 * foundation; the polished auth screens may be revisited with the feature work.
 */
export function LoginPage() {
  const { login, verifyMfa } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = (location.state as FromState | null)?.from?.pathname ?? '/';

  const [step, setStep] = useState<Step>('credentials');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [mfaToken, setMfaToken] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function describe(err: unknown): string {
    if (err instanceof ApiError) return err.message;
    return 'Something went wrong. Please try again.';
  }

  async function handleCredentials(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await login(email, password);
      if (res.mfa_required) {
        setMfaToken(res.mfa_token ?? '');
        setStep('mfa');
      } else {
        navigate(redirectTo, { replace: true });
      }
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleMfa(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await verifyMfa(mfaToken, code);
      navigate(redirectTo, { replace: true });
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="login">
      <div className="login__bg" aria-hidden="true">
        <span className="login__blob login__blob--1" />
        <span className="login__blob login__blob--2" />
      </div>

      <Card className="login__card" raised>
        <div className="login__header">
          <Logo className="login__logo" size={44} animated />
          <h1 className="login__title">piigacourse</h1>
          <p className="login__subtitle">
            {step === 'credentials'
              ? 'Sign in to your account'
              : 'Enter your code'}
          </p>
        </div>

        <div className="login__steps">
          {step === 'credentials' ? (
            <div className="login__step" key="credentials">
              <form onSubmit={handleCredentials} className="login__form">
                <Input
                  label="Email"
                  type="email"
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
                <Input
                  label="Password"
                  type="password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />
                {error && (
                  <span
                    className="field__hint field__hint--error login__error"
                    role="alert"
                  >
                    {error}
                  </span>
                )}
                <Button type="submit" block disabled={busy}>
                  {busy ? 'Signing in…' : 'Sign in'}
                </Button>
              </form>
            </div>
          ) : (
            <div className="login__step" key="mfa">
              <form onSubmit={handleMfa} className="login__form">
                <Input
                  label="Authentication code"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]*"
                  maxLength={6}
                  placeholder="123456"
                  value={code}
                  onChange={(e) =>
                    setCode(e.target.value.replace(/\D/g, '').slice(0, 6))
                  }
                  required
                />
                {error && (
                  <span
                    className="field__hint field__hint--error login__error"
                    role="alert"
                  >
                    {error}
                  </span>
                )}
                <Button type="submit" block disabled={busy}>
                  {busy ? 'Verifying…' : 'Verify'}
                </Button>
              </form>
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
