import type { CSSProperties } from 'react';
import { StatTile } from '../components/StatTile';
import { StatusBadge } from '../components/Badge';
import { Card } from '../components/Card';
import {
  GridIcon,
  LayersIcon,
  ClockIcon,
  FlameIcon,
  ActivityIcon,
  ExternalLinkIcon,
  MonitorIcon,
} from '../components/icons';
import { ApiError } from '../lib/api';
import { useAuth } from '../features/auth/AuthContext';
import { useCourses, useStats } from '../features/courses/hooks';
import './dashboard.css';

function describe(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'Something went wrong.';
}

export function DashboardPage() {
  const { user } = useAuth();
  const statsQuery = useStats();
  const inProgressQuery = useCourses('in_progress');

  const stats = statsQuery.data;
  const inProgress = inProgressQuery.data ?? [];

  return (
    <div className="dash">
      <div className="page__header">
        <div className="page__head">
          <span className="page__icon">
            <GridIcon />
          </span>
          <div>
            <h1 className="page__title">Dashboard</h1>
            <p className="page__subtitle">
              Your learning at a glance.
              {user?.email && (
                <>
                  {' '}
                  <span className="page__greeting">
                    <strong>{user.email}</strong>
                  </span>
                </>
              )}
            </p>
          </div>
        </div>
      </div>

      {statsQuery.isLoading ? (
        <div className="stat-grid" aria-hidden="true">
          {Array.from({ length: 4 }, (_, i) => (
            <div key={i} className="stat-tile dash__stat-skel">
              <span className="skel dash__stat-skel-icon" />
              <div className="dash__stat-skel-body">
                <span className="skel dash__stat-skel-num" />
                <span className="skel dash__stat-skel-label" />
              </div>
            </div>
          ))}
        </div>
      ) : statsQuery.isError ? (
        <p className="error-text">{describe(statsQuery.error)}</p>
      ) : stats ? (
        <div className="stat-grid">
          <StatTile
            className="rise"
            style={{ '--rise-delay': '0ms' } as CSSProperties}
            icon={<LayersIcon />}
            label="Active courses"
            value={stats.active_courses}
            hint={`${stats.total_courses} total`}
          />
          <StatTile
            className="rise"
            style={{ '--rise-delay': '40ms' } as CSSProperties}
            icon={<ClockIcon />}
            label="Total hours"
            value={stats.total_hours}
            hint={`${stats.total_minutes} minutes`}
          />
          <StatTile
            className="rise"
            style={{ '--rise-delay': '80ms' } as CSSProperties}
            accent
            icon={<FlameIcon />}
            label="Current streak"
            value={stats.current_streak}
            hint={stats.current_streak === 1 ? 'day' : 'days'}
          />
          <StatTile
            className="rise"
            style={{ '--rise-delay': '120ms' } as CSSProperties}
            accent
            icon={<ActivityIcon />}
            label="Sessions this week"
            value={stats.sessions_this_week}
          />
        </div>
      ) : null}

      <Card
        className="dash__panel"
        titleBar="~/courses/in-progress"
        titleBarMeta={
          inProgress.length > 0 ? `${inProgress.length} active` : undefined
        }
      >
        <div className="term-body">
          {inProgressQuery.isLoading ? (
            <p className="muted">Loading courses…</p>
          ) : inProgressQuery.isError ? (
            <p className="error-text">{describe(inProgressQuery.error)}</p>
          ) : inProgress.length === 0 ? (
            <p className="dash__empty mono">
              // nothing in progress — start a course
            </p>
          ) : (
            <div className="stack">
              {inProgress.map((course, i) => (
                <div
                  className="course-row course-row--hover rise"
                  key={course.id}
                  style={{ '--rise-delay': `${i * 40}ms` } as CSSProperties}
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
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </div>
  );
}
