"""Tests for the auth + TOTP MFA API (happy path + error cases)."""

from __future__ import annotations

import uuid

import pyotp
import pytest

from app.security import (
    create_access_token,
    create_mfa_pending_token,
    decode_mfa_pending_token,
    decode_token,
    generate_backup_codes,
    generate_totp_secret,
    verify_totp,
)

pytestmark = pytest.mark.asyncio


# --- Unit: token typing isolation -----------------------------------------


async def test_mfa_pending_token_rejected_as_access_token():
    uid = uuid.uuid4()
    pending = create_mfa_pending_token(uid)
    with pytest.raises(Exception):
        decode_token(pending)  # must reject typ=mfa_pending


async def test_access_token_rejected_as_mfa_pending():
    uid = uuid.uuid4()
    access = create_access_token(uid)
    with pytest.raises(Exception):
        decode_mfa_pending_token(access)


async def test_mfa_pending_roundtrips_for_its_own_decoder():
    uid = uuid.uuid4()
    claims = decode_mfa_pending_token(create_mfa_pending_token(uid))
    assert claims["sub"] == str(uid)
    assert claims["typ"] == "mfa_pending"


def test_verify_totp_window():
    secret = generate_totp_secret()
    assert verify_totp(secret, pyotp.TOTP(secret).now())
    assert not verify_totp(secret, "000000")


def test_generate_backup_codes_shapes():
    plain, hashed = generate_backup_codes(8)
    assert len(plain) == len(hashed) == 8
    assert all(p not in hashed for p in plain)  # only hashes stored


# --- Login (no MFA) -------------------------------------------------------


async def test_login_success_no_mfa(client, user):
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "s3cret-pw"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mfa_required"] is False
    assert body["mfa_token"] is None
    assert body["access_token"]
    # Returned token is a usable access token.
    assert decode_token(body["access_token"])["sub"] == str(user.id)


async def test_login_wrong_password(client, user):
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "nope"},
    )
    assert r.status_code == 401


async def test_login_unknown_email(client, user):
    r = await client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "s3cret-pw"},
    )
    assert r.status_code == 401


# --- /me ------------------------------------------------------------------


async def test_me_requires_auth(client, user):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_rejects_mfa_pending_token(client, user):
    pending = create_mfa_pending_token(user.id)
    r = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {pending}"}
    )
    assert r.status_code == 401


async def test_me_returns_user_without_secrets(client, user):
    token = create_access_token(user.id)
    r = await client.get(
        "/api/auth/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == user.email
    assert body["totp_enabled"] is False
    assert "password_hash" not in body
    assert "totp_secret" not in body
    assert "backup_codes" not in body


# --- Enrollment + two-step login ------------------------------------------


async def _enroll_and_enable(client, user) -> tuple[str, list[str]]:
    """Enroll + enable MFA, returning (secret, backup_codes)."""
    token = create_access_token(user.id)
    auth = {"Authorization": f"Bearer {token}"}

    r = await client.post("/api/auth/mfa/enroll", headers=auth)
    assert r.status_code == 200
    enroll = r.json()
    secret = enroll["secret"]
    assert enroll["otpauth_uri"].startswith("otpauth://")

    code = pyotp.TOTP(secret).now()
    r = await client.post(
        "/api/auth/mfa/enroll/verify", json={"code": code}, headers=auth
    )
    assert r.status_code == 200
    verify = r.json()
    assert verify["totp_enabled"] is True
    assert len(verify["backup_codes"]) == 8
    return secret, verify["backup_codes"]


async def test_full_mfa_enrollment_and_login(client, user):
    secret, backup_codes = await _enroll_and_enable(client, user)

    # Login now demands MFA.
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "s3cret-pw"},
    )
    assert r.status_code == 200
    login = r.json()
    assert login["mfa_required"] is True
    assert login["access_token"] is None
    mfa_token = login["mfa_token"]
    assert mfa_token

    # Wrong code -> 401.
    bad = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": "000000"},
    )
    assert bad.status_code == 401

    # Correct TOTP -> access token.
    good = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": pyotp.TOTP(secret).now()},
    )
    assert good.status_code == 200
    assert decode_token(good.json()["access_token"])["sub"] == str(user.id)


async def test_mfa_verify_with_backup_code_is_single_use(client, user):
    _secret, backup_codes = await _enroll_and_enable(client, user)
    code = backup_codes[0]

    def _fresh_mfa_token():
        return create_mfa_pending_token(user.id)

    # First use succeeds.
    r1 = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": _fresh_mfa_token(), "code": code},
    )
    assert r1.status_code == 200

    # Reusing the same backup code fails (consumed).
    r2 = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": _fresh_mfa_token(), "code": code},
    )
    assert r2.status_code == 401


async def test_mfa_verify_rejects_bad_token(client, user):
    await _enroll_and_enable(client, user)
    r = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": "garbage.token.value", "code": "000000"},
    )
    assert r.status_code == 401


async def test_mfa_verify_rejects_access_token_as_mfa_token(client, user):
    secret, _ = await _enroll_and_enable(client, user)
    access = create_access_token(user.id)
    r = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": access, "code": pyotp.TOTP(secret).now()},
    )
    assert r.status_code == 401  # access token is not a pending token


async def test_enroll_verify_wrong_code(client, user):
    token = create_access_token(user.id)
    auth = {"Authorization": f"Bearer {token}"}
    await client.post("/api/auth/mfa/enroll", headers=auth)
    r = await client.post(
        "/api/auth/mfa/enroll/verify", json={"code": "000000"}, headers=auth
    )
    assert r.status_code == 401


# --- Disable --------------------------------------------------------------


async def test_mfa_disable_requires_valid_code(client, user):
    secret, _ = await _enroll_and_enable(client, user)
    token = create_access_token(user.id)
    auth = {"Authorization": f"Bearer {token}"}

    bad = await client.post(
        "/api/auth/mfa/disable", json={"code": "000000"}, headers=auth
    )
    assert bad.status_code == 401

    good = await client.post(
        "/api/auth/mfa/disable",
        json={"code": pyotp.TOTP(secret).now()},
        headers=auth,
    )
    assert good.status_code == 200
    assert good.json()["totp_enabled"] is False

    # Login no longer requires MFA.
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "s3cret-pw"},
    )
    assert r.json()["mfa_required"] is False


# --- Rate limiting (H4) ---------------------------------------------------


async def test_login_lockout_after_repeated_failures(client, user):
    # 5 wrong-password attempts then a 6th -> locked out (429).
    for _ in range(5):
        r = await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong"},
        )
        assert r.status_code == 401
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong"},
    )
    assert r.status_code == 429
    assert "Retry-After" in r.headers
    # Even the correct password is refused while locked.
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "s3cret-pw"},
    )
    assert r.status_code == 429


async def test_login_success_resets_failure_counter(client, user):
    # 4 failures (below threshold) then a success clears the counter.
    for _ in range(4):
        await client.post(
            "/api/auth/login",
            json={"email": user.email, "password": "wrong"},
        )
    ok = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "s3cret-pw"},
    )
    assert ok.status_code == 200
    # Counter reset: another wrong attempt is a plain 401, not a 429.
    r = await client.post(
        "/api/auth/login",
        json={"email": user.email, "password": "wrong"},
    )
    assert r.status_code == 401


async def test_mfa_verify_lockout(client, user):
    secret, _ = await _enroll_and_enable(client, user)
    for _ in range(5):
        r = await client.post(
            "/api/auth/mfa/verify",
            json={
                "mfa_token": create_mfa_pending_token(user.id),
                "code": "000000",
            },
        )
        assert r.status_code == 401
    # 6th attempt (even with a valid code) is locked out.
    r = await client.post(
        "/api/auth/mfa/verify",
        json={
            "mfa_token": create_mfa_pending_token(user.id),
            "code": pyotp.TOTP(secret).now(),
        },
    )
    assert r.status_code == 429


# --- TOTP replay protection (H3) ------------------------------------------


async def test_mfa_verify_rejects_replayed_totp(client, user):
    secret, _ = await _enroll_and_enable(client, user)
    code = pyotp.TOTP(secret).now()

    r1 = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": create_mfa_pending_token(user.id), "code": code},
    )
    assert r1.status_code == 200

    # Same code, same timestep -> replay rejected.
    r2 = await client.post(
        "/api/auth/mfa/verify",
        json={"mfa_token": create_mfa_pending_token(user.id), "code": code},
    )
    assert r2.status_code == 401


# --- Enroll guard (M3) ----------------------------------------------------


async def test_enroll_rejected_when_already_enabled(client, user):
    await _enroll_and_enable(client, user)
    token = create_access_token(user.id)
    r = await client.post(
        "/api/auth/mfa/enroll",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
