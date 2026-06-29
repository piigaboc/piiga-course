import { useEffect, useRef, useState, type FormEvent } from 'react';
import QRCode from 'qrcode';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Badge } from '../components/Badge';
import {
  SettingsIcon,
  UserIcon,
  ShieldIcon,
  CopyIcon,
  DownloadIcon,
} from '../components/icons';
import { useAuth } from '../features/auth/AuthContext';
import { api, ApiError } from '../lib/api';
import type {
  MfaDisableResponse,
  MfaEnrollResponse,
  MfaEnrollVerifyResponse,
} from '../lib/types';
import './settings.css';

function describe(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'Something went wrong. Please try again.';
}

function sanitizeCode(v: string): string {
  return v.replace(/\D/g, '').slice(0, 6);
}

export function SettingsPage() {
  const { user } = useAuth();
  // Track local enabled state so the UI updates after enroll/disable without
  // a full app reload (useAuth().user only refreshes on (re)login).
  const [enabled, setEnabled] = useState<boolean>(
    Boolean(user?.totp_enabled),
  );

  useEffect(() => {
    setEnabled(Boolean(user?.totp_enabled));
  }, [user?.totp_enabled]);

  return (
    <div className="settings">
      <div className="page__header">
        <div className="page__head">
          <span className="page__icon">
            <SettingsIcon />
          </span>
          <div>
            <h1 className="page__title">Settings</h1>
            <p className="page__subtitle">Account and security.</p>
          </div>
        </div>
      </div>

      <div className="stack settings__col">
        <Card titleBar="~/account">
          <div className="term-body">
            <div className="settings__row">
              <span className="settings__row-icon" aria-hidden="true">
                <UserIcon />
              </span>
              <div>
                <div className="settings__row-label">Signed in as</div>
                <div className="settings__email mono">
                  {user?.email ?? '—'}
                </div>
              </div>
            </div>
          </div>
        </Card>

        <Card titleBar="~/security/mfa">
          <div className="term-body">
            <div className="settings__row settings__row--between">
              <div className="settings__row-group">
                <span className="settings__row-icon" aria-hidden="true">
                  <ShieldIcon />
                </span>
                <div>
                  <div className="settings__row-label">
                    Two-factor authentication
                  </div>
                  <div className="muted settings__hint">
                    Time-based one-time passwords (TOTP).
                  </div>
                </div>
              </div>
              {enabled ? (
                <Badge variant="completed" className="settings__mfa-badge">
                  <span className="settings__dot settings__dot--on" aria-hidden="true" />
                  Enabled
                </Badge>
              ) : (
                <Badge variant="neutral" className="settings__mfa-badge">
                  <span className="settings__dot" aria-hidden="true" />
                  Not enabled
                </Badge>
              )}
            </div>

            <div className="settings__mfa-body">
              {enabled ? (
                <DisableMfa onDisabled={() => setEnabled(false)} />
              ) : (
                <EnableMfa onEnabled={() => setEnabled(true)} />
              )}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

type EnrollStep = 'idle' | 'enrolling' | 'verify' | 'done';

function EnableMfa({ onEnabled }: { onEnabled: () => void }) {
  const [step, setStep] = useState<EnrollStep>('idle');
  const [enroll, setEnroll] = useState<MfaEnrollResponse | null>(null);
  const [code, setCode] = useState('');
  const [backupCodes, setBackupCodes] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Draw the otpauth_uri as a scannable QR once enrollment data arrives.
  useEffect(() => {
    if (step === 'verify' && enroll && canvasRef.current) {
      void QRCode.toCanvas(canvasRef.current, enroll.otpauth_uri, {
        width: 192,
        margin: 1,
      }).catch(() => {
        /* QR draw failed — the secret text below is the fallback */
      });
    }
  }, [step, enroll]);

  async function startEnroll() {
    setError(null);
    setBusy(true);
    setStep('enrolling');
    try {
      const res = await api.post<MfaEnrollResponse>('/auth/mfa/enroll');
      setEnroll(res);
      setStep('verify');
    } catch (err) {
      setError(describe(err));
      setStep('idle');
    } finally {
      setBusy(false);
    }
  }

  async function verify(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const res = await api.post<MfaEnrollVerifyResponse>(
        '/auth/mfa/enroll/verify',
        { code },
      );
      setBackupCodes(res.backup_codes);
      setStep('done');
      onEnabled();
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(false);
    }
  }

  function copyCodes() {
    void navigator.clipboard?.writeText(backupCodes.join('\n'));
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  }

  function downloadCodes() {
    const blob = new Blob([backupCodes.join('\n')], { type: 'text/plain' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'piigacourse-backup-codes.txt';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  if (step === 'done') {
    return (
      <div className="stack">
        <p>
          Two-factor authentication is now <strong>enabled</strong>. Save your
          backup codes — each can be used once if you lose your authenticator.
        </p>
        <p className="warn-text">
          These codes are shown only once. Store them somewhere safe now.
        </p>
        <ol className="backup-codes" aria-label="Backup codes">
          {backupCodes.map((c) => (
            <li key={c}>{c}</li>
          ))}
        </ol>
        <div className="settings__actions">
          <Button variant="secondary" size="sm" onClick={copyCodes}>
            <CopyIcon />
            {copied ? 'Copied' : 'Copy codes'}
          </Button>
          <Button variant="secondary" size="sm" onClick={downloadCodes}>
            <DownloadIcon />
            Download .txt
          </Button>
        </div>
      </div>
    );
  }

  if (step === 'verify' && enroll) {
    return (
      <form className="stack" onSubmit={verify}>
        <p className="muted">
          Scan this QR code with your authenticator app, then enter the 6-digit
          code to confirm.
        </p>
        <canvas
          ref={canvasRef}
          aria-label="TOTP enrollment QR code"
          width={192}
          height={192}
          className="settings__qr"
        />
        <p className="muted settings__secret">
          Or enter this secret manually:{' '}
          <code className="settings__secret-code">{enroll.secret}</code>
        </p>
        <Input
          label="Authentication code"
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={6}
          placeholder="123456"
          className="settings__code-input mono"
          value={code}
          onChange={(e) => setCode(sanitizeCode(e.target.value))}
          required
        />
        {error && <span className="error-text">{error}</span>}
        <div className="settings__actions">
          <Button type="submit" disabled={busy || code.length !== 6}>
            {busy ? 'Verifying…' : 'Confirm'}
          </Button>
        </div>
      </form>
    );
  }

  return (
    <div className="stack">
      <p className="muted">
        Add an extra layer of security using a TOTP authenticator app.
      </p>
      {error && <span className="error-text">{error}</span>}
      <div>
        <Button onClick={startEnroll} disabled={busy}>
          <ShieldIcon size={15} />
          {busy ? 'Starting…' : 'Enable TOTP MFA'}
        </Button>
      </div>
    </div>
  );
}

function DisableMfa({ onDisabled }: { onDisabled: () => void }) {
  const [code, setCode] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function disable(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      await api.post<MfaDisableResponse>('/auth/mfa/disable', { code });
      onDisabled();
    } catch (err) {
      setError(describe(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={disable}>
      <p className="muted">
        Enter a current authentication code to turn off two-factor
        authentication.
      </p>
      <Input
        label="Authentication code"
        inputMode="numeric"
        pattern="[0-9]*"
        maxLength={6}
        placeholder="123456"
        className="settings__code-input mono"
        value={code}
        onChange={(e) => setCode(sanitizeCode(e.target.value))}
        required
      />
      {error && <span className="error-text">{error}</span>}
      <div>
        <Button
          variant="destructive"
          type="submit"
          disabled={busy || code.length !== 6}
        >
          {busy ? 'Disabling…' : 'Disable MFA'}
        </Button>
      </div>
    </form>
  );
}
