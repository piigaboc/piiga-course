"""Study-session endpoints + the "which days did I study" calendar.

Mounted under ``/api`` (the parent router carries the ``/api`` prefix). Session
creation/listing live under ``/api/courses/{course_id}/sessions``; deletion and
the calendar aggregation live under ``/api/sessions/...``. Every route requires
an authenticated user; ownership is enforced through the parent course
(``Course.user_id == current_user.id``) and returns ``404`` when not owned.
"""

from __future__ import annotations

import calendar as _calendar
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Course, StudySession, User
from app.schemas import (
    CalendarDay,
    CalendarResponse,
    SessionCreate,
    SessionOut,
)
from app.security import get_current_user

router = APIRouter(tags=["sessions"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
)


async def _get_owned_course(
    course_id: uuid.UUID, user: User, db: AsyncSession
) -> Course:
    course = await db.get(Course, course_id)
    if course is None or course.user_id != user.id:
        raise _NOT_FOUND
    return course


@router.post(
    "/courses/{course_id}/sessions",
    response_model=SessionOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    course_id: uuid.UUID,
    payload: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StudySession:
    """Log a study session against an owned course (404 if not owned)."""
    await _get_owned_course(course_id, current_user, db)
    study = StudySession(
        course_id=course_id,
        date=payload.date,
        minutes=payload.minutes,
        note=payload.note,
    )
    db.add(study)
    await db.commit()
    await db.refresh(study)
    return study


@router.get(
    "/courses/{course_id}/sessions",
    response_model=list[SessionOut],
)
async def list_sessions(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[StudySession]:
    """List sessions for an owned course (most recent date first)."""
    await _get_owned_course(course_id, current_user, db)
    stmt = (
        select(StudySession)
        .where(StudySession.course_id == course_id)
        .order_by(StudySession.date.desc(), StudySession.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_session(
    session_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a session whose course is owned by the user (404 otherwise)."""
    study = await db.get(StudySession, session_id)
    if study is None:
        raise _NOT_FOUND
    course = await db.get(Course, study.course_id)
    if course is None or course.user_id != current_user.id:
        raise _NOT_FOUND
    await db.delete(study)
    await db.commit()


def _parse_month(month: str | None) -> tuple[str, date, date]:
    """Return ``(month_str, first_day, last_day)`` for ``YYYY-MM``.

    Defaults to the current month when ``month`` is omitted. Raises 422 on a
    malformed value.
    """
    if month is None:
        today = date.today()
        year, mon = today.year, today.month
    else:
        try:
            year_s, mon_s = month.split("-")
            year, mon = int(year_s), int(mon_s)
            if not (1 <= mon <= 12) or len(mon_s) != 2 or len(year_s) != 4:
                raise ValueError
        except (ValueError, AttributeError) as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="month must be in YYYY-MM format",
            ) from exc
    first = date(year, mon, 1)
    last = date(year, mon, _calendar.monthrange(year, mon)[1])
    return f"{year:04d}-{mon:02d}", first, last


@router.get("/sessions/calendar", response_model=CalendarResponse)
async def study_calendar(
    month: str | None = Query(default=None, description="Target month YYYY-MM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CalendarResponse:
    """Aggregate the user's study sessions for ``month`` grouped by day.

    Powers the "เรียนวันไหนบ้าง" calendar: one entry per day that had at least
    one session, with total minutes, session count, and the distinct courses
    studied that day. Uses a single grouped query joining courses -> sessions.
    """
    month_str, first, last = _parse_month(month)

    stmt = (
        select(
            StudySession.date,
            func.sum(StudySession.minutes),
            func.count(StudySession.id),
        )
        .join(Course, Course.id == StudySession.course_id)
        .where(
            Course.user_id == current_user.id,
            StudySession.date >= first,
            StudySession.date <= last,
        )
        .group_by(StudySession.date)
        .order_by(StudySession.date)
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Second grouped query for the distinct course ids per day (kept separate
    # so the aggregate counts stay exact and dialect-portable).
    course_stmt = (
        select(StudySession.date, StudySession.course_id)
        .join(Course, Course.id == StudySession.course_id)
        .where(
            Course.user_id == current_user.id,
            StudySession.date >= first,
            StudySession.date <= last,
        )
        .distinct()
    )
    course_rows = (await db.execute(course_stmt)).all()
    by_day: dict[date, list[uuid.UUID]] = {}
    for day, course_id in course_rows:
        by_day.setdefault(day, []).append(course_id)

    days = [
        CalendarDay(
            date=day,
            total_minutes=int(total or 0),
            session_count=int(count or 0),
            course_ids=by_day.get(day, []),
        )
        for day, total, count in rows
    ]
    return CalendarResponse(month=month_str, days=days)
