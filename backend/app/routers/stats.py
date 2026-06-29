"""Dashboard statistics for the single user.

Mounted under ``/api`` (the parent router carries the ``/api`` prefix) as
``GET /api/stats``. All figures are scoped to the authenticated user via
``Course.user_id == current_user.id``.
"""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Course, CourseStatus, StudySession, User
from app.schemas import StatsOut
from app.security import get_current_user

router = APIRouter(tags=["stats"])


def _current_streak(study_dates: set[date], today: date) -> int:
    """Count consecutive days with >=1 session ending today or yesterday.

    The streak anchors on ``today`` if studied today, else on ``yesterday`` so
    that a not-yet-studied today does not break an active streak. Returns 0 if
    neither today nor yesterday has a session.
    """
    if today in study_dates:
        cursor = today
    elif (today - timedelta(days=1)) in study_dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in study_dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


@router.get("/stats", response_model=StatsOut)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StatsOut:
    """Summary stats: course counts, total study time, streak, weekly volume."""
    uid = current_user.id

    # Course counts by status (single grouped query).
    count_stmt = (
        select(Course.status, func.count(Course.id))
        .where(Course.user_id == uid)
        .group_by(Course.status)
    )
    counts = dict((await db.execute(count_stmt)).all())
    active_courses = int(counts.get(CourseStatus.in_progress, 0))
    completed_courses = int(counts.get(CourseStatus.completed, 0))
    total_courses = int(sum(counts.values()))

    # Total minutes across all of the user's sessions.
    minutes_stmt = (
        select(func.coalesce(func.sum(StudySession.minutes), 0))
        .join(Course, Course.id == StudySession.course_id)
        .where(Course.user_id == uid)
    )
    total_minutes = int((await db.execute(minutes_stmt)).scalar_one())

    today = date.today()
    week_ago = today - timedelta(days=7)

    # Sessions in the last 7 days (inclusive of week_ago .. today).
    week_stmt = (
        select(func.count(StudySession.id))
        .join(Course, Course.id == StudySession.course_id)
        .where(
            Course.user_id == uid,
            StudySession.date >= week_ago,
            StudySession.date <= today,
        )
    )
    sessions_this_week = int((await db.execute(week_stmt)).scalar_one())

    # Distinct session dates for streak computation (in Python).
    dates_stmt = (
        select(StudySession.date)
        .join(Course, Course.id == StudySession.course_id)
        .where(Course.user_id == uid)
        .distinct()
    )
    study_dates = {d for (d,) in (await db.execute(dates_stmt)).all()}

    return StatsOut(
        active_courses=active_courses,
        completed_courses=completed_courses,
        total_courses=total_courses,
        total_minutes=total_minutes,
        total_hours=round(total_minutes / 60, 1),
        current_streak=_current_streak(study_dates, today),
        sessions_this_week=sessions_this_week,
    )
