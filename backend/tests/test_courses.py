"""Tests for courses / study-sessions / calendar / stats API.

Happy paths plus ownership (404, never 403) and validation error cases. Auth is
exercised via a real access token for the seeded ``user`` fixture.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest

from app.models import Course, CourseStatus, StudySession
from app.security import create_access_token

pytestmark = pytest.mark.asyncio


def _auth(user) -> dict[str, str]:  # noqa: ANN001
    return {"Authorization": f"Bearer {create_access_token(user.id)}"}


# --- Courses CRUD ---------------------------------------------------------


async def test_create_and_get_course(client, user):  # noqa: ANN001
    auth = _auth(user)
    r = await client.post(
        "/api/courses",
        json={"title": "FastAPI 101", "platform": "Udemy"},
        headers=auth,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "FastAPI 101"
    assert body["status"] == "planned"
    course_id = body["id"]

    r = await client.get(f"/api/courses/{course_id}", headers=auth)
    assert r.status_code == 200
    assert r.json()["platform"] == "Udemy"


async def test_list_courses_and_status_filter(client, user):  # noqa: ANN001
    auth = _auth(user)
    for title, st in [("a", "planned"), ("b", "in_progress")]:
        await client.post(
            "/api/courses", json={"title": title, "status": st}, headers=auth
        )
    r = await client.get("/api/courses", headers=auth)
    assert r.status_code == 200
    assert {c["title"] for c in r.json()} == {"a", "b"}

    r = await client.get("/api/courses?status=in_progress", headers=auth)
    assert [c["title"] for c in r.json()] == ["b"]


async def test_patch_course(client, user):  # noqa: ANN001
    auth = _auth(user)
    course_id = (
        await client.post("/api/courses", json={"title": "x"}, headers=auth)
    ).json()["id"]
    r = await client.patch(
        f"/api/courses/{course_id}",
        json={"status": "completed"},
        headers=auth,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "completed"


async def test_delete_course_cascades_sessions(client, user, session_factory):  # noqa: ANN001
    auth = _auth(user)
    course_id = (
        await client.post("/api/courses", json={"title": "x"}, headers=auth)
    ).json()["id"]
    await client.post(
        f"/api/courses/{course_id}/sessions",
        json={"date": str(date.today()), "minutes": 30},
        headers=auth,
    )
    r = await client.delete(f"/api/courses/{course_id}", headers=auth)
    assert r.status_code == 204
    async with session_factory() as s:
        rows = (await s.execute(StudySession.__table__.select())).all()
        assert rows == []


async def test_course_404_when_missing(client, user):  # noqa: ANN001
    r = await client.get(f"/api/courses/{uuid.uuid4()}", headers=_auth(user))
    assert r.status_code == 404


async def test_course_404_when_not_owned(client, user, session_factory):  # noqa: ANN001
    # A course owned by someone else must read as 404, not 403.
    other_id = uuid.uuid4()
    async with session_factory() as s:
        c = Course(id=other_id, user_id=uuid.uuid4(), title="theirs")
        s.add(c)
        await s.commit()
    r = await client.get(f"/api/courses/{other_id}", headers=_auth(user))
    assert r.status_code == 404


async def test_unauthenticated_rejected(client):  # noqa: ANN001
    assert (await client.get("/api/courses")).status_code == 401


# --- Sessions -------------------------------------------------------------


async def test_create_list_delete_session(client, user):  # noqa: ANN001
    auth = _auth(user)
    course_id = (
        await client.post("/api/courses", json={"title": "x"}, headers=auth)
    ).json()["id"]
    r = await client.post(
        f"/api/courses/{course_id}/sessions",
        json={"date": "2026-06-01", "minutes": 45, "note": "hi"},
        headers=auth,
    )
    assert r.status_code == 201
    sid = r.json()["id"]

    await client.post(
        f"/api/courses/{course_id}/sessions",
        json={"date": "2026-06-10", "minutes": 20},
        headers=auth,
    )
    r = await client.get(f"/api/courses/{course_id}/sessions", headers=auth)
    dates = [s["date"] for s in r.json()]
    assert dates == ["2026-06-10", "2026-06-01"]  # date desc

    r = await client.delete(f"/api/sessions/{sid}", headers=auth)
    assert r.status_code == 204


async def test_session_minutes_must_be_positive(client, user):  # noqa: ANN001
    auth = _auth(user)
    course_id = (
        await client.post("/api/courses", json={"title": "x"}, headers=auth)
    ).json()["id"]
    r = await client.post(
        f"/api/courses/{course_id}/sessions",
        json={"date": "2026-06-01", "minutes": 0},
        headers=auth,
    )
    assert r.status_code == 422


async def test_session_on_unowned_course_404(client, user):  # noqa: ANN001
    r = await client.post(
        f"/api/courses/{uuid.uuid4()}/sessions",
        json={"date": "2026-06-01", "minutes": 10},
        headers=_auth(user),
    )
    assert r.status_code == 404


async def test_delete_unowned_session_404(client, user):  # noqa: ANN001
    r = await client.delete(
        f"/api/sessions/{uuid.uuid4()}", headers=_auth(user)
    )
    assert r.status_code == 404


# --- Calendar -------------------------------------------------------------


async def test_calendar_aggregates_by_day(client, user):  # noqa: ANN001
    auth = _auth(user)
    c1 = (
        await client.post("/api/courses", json={"title": "c1"}, headers=auth)
    ).json()["id"]
    c2 = (
        await client.post("/api/courses", json={"title": "c2"}, headers=auth)
    ).json()["id"]
    # Two sessions same day across two courses + one another day.
    for cid, d, m in [
        (c1, "2026-06-05", 30),
        (c2, "2026-06-05", 20),
        (c1, "2026-06-07", 15),
    ]:
        await client.post(
            f"/api/courses/{cid}/sessions",
            json={"date": d, "minutes": m},
            headers=auth,
        )
    r = await client.get("/api/sessions/calendar?month=2026-06", headers=auth)
    assert r.status_code == 200
    body = r.json()
    assert body["month"] == "2026-06"
    days = {d["date"]: d for d in body["days"]}
    assert days["2026-06-05"]["total_minutes"] == 50
    assert days["2026-06-05"]["session_count"] == 2
    assert len(days["2026-06-05"]["course_ids"]) == 2
    assert days["2026-06-07"]["total_minutes"] == 15


async def test_calendar_bad_month_422(client, user):  # noqa: ANN001
    r = await client.get(
        "/api/sessions/calendar?month=2026-13", headers=_auth(user)
    )
    assert r.status_code == 422


async def test_calendar_defaults_to_current_month(client, user):  # noqa: ANN001
    r = await client.get("/api/sessions/calendar", headers=_auth(user))
    assert r.status_code == 200
    assert r.json()["month"] == date.today().strftime("%Y-%m")


# --- Stats ----------------------------------------------------------------


async def test_stats(client, user):  # noqa: ANN001
    auth = _auth(user)
    c_active = (
        await client.post(
            "/api/courses",
            json={"title": "a", "status": "in_progress"},
            headers=auth,
        )
    ).json()["id"]
    await client.post(
        "/api/courses",
        json={"title": "b", "status": "completed"},
        headers=auth,
    )
    today = date.today()
    for offset, m in [(0, 60), (1, 30)]:  # today + yesterday -> streak 2
        await client.post(
            f"/api/courses/{c_active}/sessions",
            json={"date": str(today - timedelta(days=offset)), "minutes": m},
            headers=auth,
        )
    r = await client.get("/api/stats", headers=auth)
    assert r.status_code == 200
    s = r.json()
    assert s["active_courses"] == 1
    assert s["completed_courses"] == 1
    assert s["total_courses"] == 2
    assert s["total_minutes"] == 90
    assert s["total_hours"] == 1.5
    assert s["current_streak"] == 2
    assert s["sessions_this_week"] == 2
