"""Course CRUD endpoints (single-user, ownership-scoped).

Mounted under ``/api/courses`` (the parent router carries the ``/api`` prefix,
this router adds ``/courses``). Every route requires an authenticated user and
scopes queries to that user via ``Course.user_id == current_user.id``. When a
course is not found OR belongs to a different user we return ``404`` (never
``403``) so existence is not leaked.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete as sa_delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.models import Course, CourseStatus, Lesson, StudySession, User
from app.schemas import CourseCreate, CourseOut, CourseUpdate
from app.security import get_current_user

router = APIRouter(prefix="/courses", tags=["courses"])


async def _get_owned_course(
    course_id: uuid.UUID, user: User, db: AsyncSession
) -> Course:
    """Load a course owned by ``user`` or raise 404."""
    course = await db.get(Course, course_id)
    if course is None or course.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        )
    return course


@router.get("", response_model=list[CourseOut])
async def list_courses(
    status: CourseStatus | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[Course]:
    """List the current user's courses (newest first), optionally by status."""
    stmt = select(Course).where(Course.user_id == current_user.id)
    if status is not None:
        stmt = stmt.where(Course.status == status)
    stmt = stmt.order_by(Course.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


@router.post("", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Course:
    """Create a course owned by the current user."""
    course = Course(
        user_id=current_user.id,
        title=payload.title,
        platform=payload.platform,
        url=payload.url,
        status=payload.status,
        target_date=payload.target_date,
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)
    return course


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Course:
    """Fetch a single owned course (404 if not found/not owned)."""
    return await _get_owned_course(course_id, current_user, db)


@router.patch("/{course_id}", response_model=CourseOut)
async def update_course(
    course_id: uuid.UUID,
    payload: CourseUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Course:
    """Partially update an owned course (404 if not found/not owned)."""
    course = await _get_owned_course(course_id, current_user, db)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(course, field, value)
    await db.commit()
    await db.refresh(course)
    return course


@router.delete("/{course_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_course(
    course_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an owned course and its sessions/lessons.

    Children are removed explicitly so deletion is correct regardless of
    whether the backend enforces the ``ON DELETE CASCADE`` foreign keys (e.g.
    SQLite has FK enforcement off by default).
    """
    course = await _get_owned_course(course_id, current_user, db)
    await db.execute(
        sa_delete(StudySession).where(StudySession.course_id == course_id)
    )
    await db.execute(sa_delete(Lesson).where(Lesson.course_id == course_id))
    await db.delete(course)
    await db.commit()
