import { useMemo, useState, type CSSProperties, type FormEvent } from 'react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { Input } from '../components/Input';
import { Modal } from '../components/Modal';
import { StatusBadge } from '../components/Badge';
import {
  BooksIcon,
  PlusIcon,
  MonitorIcon,
  ExternalLinkIcon,
  ClockIcon,
  TrashIcon,
  CalendarIcon,
} from '../components/icons';
import { ApiError } from '../lib/api';
import type { Course, CourseStatus } from '../lib/types';
import {
  useCourses,
  useCreateCourse,
  useDeleteCourse,
  useLogSession,
  useUpdateCourse,
} from '../features/courses/hooks';
import './courses.css';

const STATUSES: CourseStatus[] = [
  'planned',
  'in_progress',
  'completed',
  'paused',
];

const STATUS_LABELS: Record<CourseStatus, string> = {
  planned: 'Planned',
  in_progress: 'In progress',
  completed: 'Completed',
  paused: 'Paused',
};

function todayISO(): string {
  return new Date().toISOString().slice(0, 10);
}

function describe(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'Something went wrong. Please try again.';
}

export function CoursesPage() {
  const [filter, setFilter] = useState<CourseStatus | 'all'>('all');
  const [addOpen, setAddOpen] = useState(false);
  const [logFor, setLogFor] = useState<Course | null>(null);

  const coursesQuery = useCourses(filter);
  const courses = coursesQuery.data ?? [];

  // Counts come from the unfiltered list so chips stay stable across filters.
  const allQuery = useCourses('all');
  const counts = useMemo(() => {
    const all = allQuery.data ?? [];
    const by: Record<string, number> = { all: all.length };
    for (const s of STATUSES) by[s] = 0;
    for (const c of all) by[c.status] = (by[c.status] ?? 0) + 1;
    return by;
  }, [allQuery.data]);

  return (
    <div className="courses">
      <div className="page__header">
        <div className="page__head">
          <span className="page__icon">
            <BooksIcon />
          </span>
          <div>
            <h1 className="page__title">Courses</h1>
            <p className="page__subtitle">
              Track the courses you are learning and log study time.
            </p>
          </div>
        </div>
        <Button onClick={() => setAddOpen(true)}>
          <PlusIcon />
          Add course
        </Button>
      </div>

      <div className="filter-bar" role="group" aria-label="Filter by status">
        <button
          type="button"
          className={
            'filter-chip' + (filter === 'all' ? ' filter-chip--active' : '')
          }
          aria-label="All"
          aria-pressed={filter === 'all'}
          onClick={() => setFilter('all')}
        >
          All
          <span className="filter-chip__count" aria-hidden="true">
            {counts.all ?? 0}
          </span>
        </button>
        {STATUSES.map((s) => (
          <button
            key={s}
            type="button"
            className={
              'filter-chip' + (filter === s ? ' filter-chip--active' : '')
            }
            aria-label={STATUS_LABELS[s]}
            aria-pressed={filter === s}
            onClick={() => setFilter(s)}
          >
            {STATUS_LABELS[s]}
            <span className="filter-chip__count" aria-hidden="true">
              {counts[s] ?? 0}
            </span>
          </button>
        ))}
      </div>

      <Card
        className="courses__panel"
        titleBar={
          filter === 'all' ? '~/courses' : `~/courses --status=${filter}`
        }
        titleBarMeta={`${courses.length} total`}
      >
        <div className="term-body">
          {coursesQuery.isLoading ? (
            <p className="muted">Loading courses…</p>
          ) : coursesQuery.isError ? (
            <p className="error-text">{describe(coursesQuery.error)}</p>
          ) : courses.length === 0 ? (
            <p className="courses__empty mono">
              // no courses yet — add one
            </p>
          ) : (
            <div className="stack">
              {courses.map((course, i) => (
                <CourseRow
                  key={course.id}
                  course={course}
                  index={i}
                  onLog={() => setLogFor(course)}
                />
              ))}
            </div>
          )}
        </div>
      </Card>

      <AddCourseModal open={addOpen} onClose={() => setAddOpen(false)} />
      {logFor && (
        <LogSessionModal course={logFor} onClose={() => setLogFor(null)} />
      )}
    </div>
  );
}

function CourseRow({
  course,
  index,
  onLog,
}: {
  course: Course;
  index: number;
  onLog: () => void;
}) {
  const updateCourse = useUpdateCourse();
  const deleteCourse = useDeleteCourse();

  function onStatusChange(status: CourseStatus) {
    updateCourse.mutate({ id: course.id, body: { status } });
  }

  function onDelete() {
    if (window.confirm(`Delete "${course.title}"? This cannot be undone.`)) {
      deleteCourse.mutate(course.id);
    }
  }

  return (
    <div
      className="course-row course-row--hover rise"
      style={{ '--rise-delay': `${index * 35}ms` } as CSSProperties}
    >
      <div className="course-row__main">
        <h3 className="course-row__title">
          {course.title}
          <StatusBadge status={course.status} />
        </h3>
        <div className="course-row__meta mono">
          {course.platform && (
            <span className="course-row__chip">
              <MonitorIcon />
              {course.platform}
            </span>
          )}
          {course.url && (
            <a
              className="course-row__link"
              href={course.url}
              target="_blank"
              rel="noreferrer noopener"
            >
              <ExternalLinkIcon />
              {course.url}
            </a>
          )}
          {course.target_date && (
            <span className="course-row__target">
              <CalendarIcon size={13} />
              target {course.target_date}
            </span>
          )}
        </div>
      </div>

      <div className="course-row__actions">
        <label className="field" style={{ minWidth: 140 }}>
          <span className="field__label" style={{ display: 'none' }}>
            Status
          </span>
          <select
            className="select"
            aria-label={`Status for ${course.title}`}
            value={course.status}
            onChange={(e) => onStatusChange(e.target.value as CourseStatus)}
            disabled={updateCourse.isPending}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <Button variant="secondary" size="sm" onClick={onLog}>
          <ClockIcon size={14} />
          Log study
        </Button>
        <Button
          variant="destructive"
          size="sm"
          onClick={onDelete}
          disabled={deleteCourse.isPending}
          aria-label={`Delete ${course.title}`}
        >
          <TrashIcon />
          Delete
        </Button>
      </div>
    </div>
  );
}

function AddCourseModal({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const createCourse = useCreateCourse();
  const [title, setTitle] = useState('');
  const [platform, setPlatform] = useState('');
  const [url, setUrl] = useState('');
  const [status, setStatus] = useState<CourseStatus>('planned');
  const [targetDate, setTargetDate] = useState('');
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setTitle('');
    setPlatform('');
    setUrl('');
    setStatus('planned');
    setTargetDate('');
    setError(null);
  }

  function close() {
    reset();
    onClose();
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await createCourse.mutateAsync({
        title: title.trim(),
        platform: platform.trim() || undefined,
        url: url.trim() || undefined,
        status,
        target_date: targetDate || undefined,
      });
      close();
    } catch (err) {
      setError(describe(err));
    }
  }

  return (
    <Modal
      open={open}
      onClose={close}
      title="Add course"
      description="Add a course you are learning."
    >
      <form id="add-course-form" onSubmit={onSubmit} className="stack">
        <Input
          label="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <Input
          label="Platform"
          placeholder="e.g. Udemy, Coursera"
          value={platform}
          onChange={(e) => setPlatform(e.target.value)}
        />
        <Input
          label="URL"
          type="url"
          placeholder="https://…"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
        />
        <div className="field">
          <label className="field__label" htmlFor="add-course-status">
            Status
          </label>
          <select
            id="add-course-status"
            className="select"
            value={status}
            onChange={(e) => setStatus(e.target.value as CourseStatus)}
          >
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </div>
        <Input
          label="Target date"
          type="date"
          value={targetDate}
          onChange={(e) => setTargetDate(e.target.value)}
        />
        {error && <span className="error-text">{error}</span>}
      </form>
      <div className="modal__footer">
        <Button variant="outline" onClick={close}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="add-course-form"
          disabled={createCourse.isPending || !title.trim()}
        >
          {createCourse.isPending ? 'Adding…' : 'Add course'}
        </Button>
      </div>
    </Modal>
  );
}

function LogSessionModal({
  course,
  onClose,
}: {
  course: Course;
  onClose: () => void;
}) {
  const logSession = useLogSession();
  const [date, setDate] = useState(todayISO());
  const [minutes, setMinutes] = useState('30');
  const [note, setNote] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const mins = Number(minutes);
    if (!Number.isFinite(mins) || mins <= 0) {
      setError('Enter the minutes you studied.');
      return;
    }
    try {
      await logSession.mutateAsync({
        courseId: course.id,
        body: { date, minutes: mins, note: note.trim() || undefined },
      });
      onClose();
    } catch (err) {
      setError(describe(err));
    }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Log study"
      description={course.title}
    >
      <form id="log-session-form" onSubmit={onSubmit} className="stack">
        <Input
          label="Date"
          type="date"
          value={date}
          onChange={(e) => setDate(e.target.value)}
          required
        />
        <Input
          label="Minutes"
          type="number"
          min={1}
          value={minutes}
          onChange={(e) => setMinutes(e.target.value)}
          required
        />
        <div className="field">
          <label className="field__label" htmlFor="log-session-note">
            Note
          </label>
          <textarea
            id="log-session-note"
            className="textarea"
            placeholder="What did you work on?"
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
        {error && <span className="error-text">{error}</span>}
      </form>
      <div className="modal__footer">
        <Button variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button
          type="submit"
          form="log-session-form"
          disabled={logSession.isPending}
        >
          {logSession.isPending ? 'Saving…' : 'Save session'}
        </Button>
      </div>
    </Modal>
  );
}
