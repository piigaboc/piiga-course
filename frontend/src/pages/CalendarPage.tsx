import { useMemo, useState, type CSSProperties } from 'react';
import { Button } from '../components/Button';
import { Card } from '../components/Card';
import { ApiError } from '../lib/api';
import type { CalendarDay } from '../lib/types';
import { useCalendar } from '../features/courses/hooks';
import './calendar.css';

// Week starts on Monday.
const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const MONTH_NAMES = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December',
];

function pad2(n: number): string {
  return String(n).padStart(2, '0');
}

function monthKey(year: number, month0: number): string {
  return `${year}-${pad2(month0 + 1)}`;
}

function isoDate(year: number, month0: number, day: number): string {
  return `${year}-${pad2(month0 + 1)}-${pad2(day)}`;
}

function describe(err: unknown): string {
  if (err instanceof ApiError) return err.message;
  return 'Could not load the calendar.';
}

/**
 * GitHub-contribution style intensity bucket from total study minutes.
 * 0 = none, 1 = 1–29m, 2 = 30–59m, 3 = 60–119m, 4 = 120m+.
 */
function intensity(minutes: number): 0 | 1 | 2 | 3 | 4 {
  if (minutes <= 0) return 0;
  if (minutes < 30) return 1;
  if (minutes < 60) return 2;
  if (minutes < 120) return 3;
  return 4;
}

interface Cell {
  date: string;
  day: number;
  inMonth: boolean;
}

/** Build a 6-row (42 cell) Mon–Sun grid covering the given month. */
function buildGrid(year: number, month0: number): Cell[] {
  const first = new Date(year, month0, 1);
  // JS: 0=Sun … 6=Sat. Convert to Mon=0 … Sun=6.
  const firstWeekday = (first.getDay() + 6) % 7;
  const cells: Cell[] = [];
  // Days from the previous month to fill the leading gap.
  for (let i = firstWeekday - 1; i >= 0; i--) {
    const d = new Date(year, month0, -i);
    cells.push({
      date: isoDate(d.getFullYear(), d.getMonth(), d.getDate()),
      day: d.getDate(),
      inMonth: false,
    });
  }
  const daysInMonth = new Date(year, month0 + 1, 0).getDate();
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({ date: isoDate(year, month0, day), day, inMonth: true });
  }
  // Trailing days to complete 42 cells.
  let next = 1;
  while (cells.length < 42) {
    const d = new Date(year, month0 + 1, next++);
    cells.push({
      date: isoDate(d.getFullYear(), d.getMonth(), d.getDate()),
      day: d.getDate(),
      inMonth: false,
    });
  }
  return cells;
}

/** Longest run of consecutive in-month studied days (streak indicator). */
function longestStreak(daysInMonth: number, studiedDays: Set<number>): number {
  let best = 0;
  let run = 0;
  for (let d = 1; d <= daysInMonth; d++) {
    if (studiedDays.has(d)) {
      run += 1;
      if (run > best) best = run;
    } else {
      run = 0;
    }
  }
  return best;
}

function formatDuration(minutes: number): string {
  if (minutes < 60) return `${minutes}m`;
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

/* ---- Inline icons (currentColor) ----------------------------------------- */

function CalendarIcon({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <rect x="3" y="4" width="18" height="18" rx="2" />
      <path d="M16 2v4M8 2v4M3 10h18" />
      <rect x="7" y="14" width="3" height="3" rx="0.5" fill="currentColor" stroke="none" />
    </svg>
  );
}

function ClockIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="9" />
      <path d="M12 7v5l3 2" />
    </svg>
  );
}

function ActivityIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
    </svg>
  );
}

function FlameIcon({ size = 16 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M12 2c1 3 4 4.5 4 8a4 4 0 0 1-8 0c0-1.2.4-2 1-3 .2 1 .8 1.6 1.5 1.8C10 7 11 4.5 12 2Z" />
      <path d="M12 22a6 6 0 0 0 6-6c0-2-1-3.5-2.3-4.8C15.5 14 14 15 12 15s-3.5-1-3.7-3.8C7 12.5 6 14 6 16a6 6 0 0 0 6 6Z" />
    </svg>
  );
}

function DotIcon({ size = 7 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 8 8" aria-hidden="true">
      <circle cx="4" cy="4" r="4" fill="currentColor" />
    </svg>
  );
}

function ChevronLeft() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

function ChevronRight() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" strokeWidth="2.2" strokeLinecap="round"
      strokeLinejoin="round" aria-hidden="true">
      <path d="M9 18l6-6-6-6" />
    </svg>
  );
}

export function CalendarPage() {
  const now = new Date();
  const [year, setYear] = useState(now.getFullYear());
  const [month0, setMonth0] = useState(now.getMonth());
  const [selected, setSelected] = useState<string | null>(null);

  const month = monthKey(year, month0);
  const calendarQuery = useCalendar(month);
  const isLoading = calendarQuery.isLoading;

  const todayISO = isoDate(now.getFullYear(), now.getMonth(), now.getDate());
  const isCurrentMonth =
    year === now.getFullYear() && month0 === now.getMonth();

  const byDate = useMemo(() => {
    const map = new Map<string, CalendarDay>();
    for (const d of calendarQuery.data?.days ?? []) map.set(d.date, d);
    return map;
  }, [calendarQuery.data]);

  const cells = useMemo(() => buildGrid(year, month0), [year, month0]);

  // Aggregate nerd-stats for the visible month (in-month days only).
  const stats = useMemo(() => {
    const daysInMonth = new Date(year, month0 + 1, 0).getDate();
    const studiedDays = new Set<number>();
    let totalMinutes = 0;
    for (let d = 1; d <= daysInMonth; d++) {
      const info = byDate.get(isoDate(year, month0, d));
      if (info && info.session_count > 0) {
        studiedDays.add(d);
        totalMinutes += info.total_minutes;
      }
    }
    return {
      totalMinutes,
      activeDays: studiedDays.size,
      streak: longestStreak(daysInMonth, studiedDays),
    };
  }, [byDate, year, month0]);

  function prevMonth() {
    setSelected(null);
    if (month0 === 0) {
      setYear((y) => y - 1);
      setMonth0(11);
    } else {
      setMonth0((m) => m - 1);
    }
  }

  function nextMonth() {
    setSelected(null);
    if (month0 === 11) {
      setYear((y) => y + 1);
      setMonth0(0);
    } else {
      setMonth0((m) => m + 1);
    }
  }

  function goToday() {
    setSelected(null);
    setYear(now.getFullYear());
    setMonth0(now.getMonth());
  }

  const selectedDay = selected ? byDate.get(selected) : undefined;
  // Stable index so the entrance stagger follows reading order.
  let studiedIndex = 0;

  return (
    <div className="cal">
      <div className="page__header">
        <div>
          <div className="cal__titlewrap">
            <span className="cal__titleicon">
              <CalendarIcon />
            </span>
            <div>
              <h1 className="page__title">Calendar</h1>
              <p className="page__subtitle" lang="th">
                เรียนวันไหนบ้าง — which days you studied this month.
              </p>
            </div>
          </div>

          <div className="cal__stats">
            <div className="cal__stat">
              <ClockIcon />
              <span className="cal__stat-num">
                {formatDuration(stats.totalMinutes)}
              </span>
              <span className="cal__stat-label">studied</span>
            </div>
            <div className="cal__stat">
              <ActivityIcon />
              <span className="cal__stat-num">{stats.activeDays}</span>
              <span className="cal__stat-label">active days</span>
            </div>
            <div className="cal__stat cal__stat--streak">
              <FlameIcon />
              <span className="cal__stat-num">{stats.streak}</span>
              <span className="cal__stat-label">day streak</span>
            </div>
          </div>
        </div>

        <div className="cal__nav calendar__nav">
          <Button
            variant="outline"
            size="sm"
            onClick={prevMonth}
            aria-label="Previous month"
            className="cal__chev"
          >
            <ChevronLeft />
          </Button>
          <span className="cal__monthlabel calendar__month-label">
            {MONTH_NAMES[month0]} {year}
          </span>
          <Button
            variant="outline"
            size="sm"
            onClick={nextMonth}
            aria-label="Next month"
            className="cal__chev"
          >
            <ChevronRight />
          </Button>
          <Button
            variant="secondary"
            size="sm"
            onClick={goToday}
            disabled={isCurrentMonth}
            aria-label="Jump to current month"
          >
            Today
          </Button>
        </div>
      </div>

      {calendarQuery.isError && (
        <p className="error-text">{describe(calendarQuery.error)}</p>
      )}

      <Card className="cal__panel">
        <div className="cal__panel-bar">
          <span className="cal__dots" aria-hidden="true">
            <i /><i /><i />
          </span>
          <span>~/study/{month} · {stats.activeDays} active</span>
        </div>

        <div className="cal__panel-body">
          <div
            className="cal__grid calendar__grid"
            role="grid"
            aria-label={`${MONTH_NAMES[month0]} ${year}`}
          >
            {WEEKDAYS.map((w) => (
              <div key={w} className="cal__weekday calendar__weekday" role="columnheader">
                {w}
              </div>
            ))}

            {isLoading
              ? Array.from({ length: 42 }, (_, i) => (
                  <div key={i} className="cal__skel" aria-hidden="true" />
                ))
              : cells.map((cell) => {
                  const info = cell.inMonth ? byDate.get(cell.date) : undefined;
                  const studied = Boolean(info && info.session_count > 0);
                  const level = studied ? intensity(info!.total_minutes) : 0;
                  const isToday = cell.date === todayISO;
                  const isSelected = cell.date === selected;
                  const delay = studied ? studiedIndex++ * 22 : 0;

                  const className = [
                    'cal__cell',
                    'calendar__cell',
                    !cell.inMonth && 'cal__cell--outside',
                    !cell.inMonth && 'calendar__cell--outside',
                    studied && 'cal__cell--studied',
                    studied && 'calendar__cell--studied',
                    studied && `cal__cell--l${level}`,
                    isToday && 'cal__cell--today',
                    isToday && 'calendar__cell--today',
                    isSelected && 'cal__cell--selected',
                    isSelected && 'calendar__cell--selected',
                  ]
                    .filter(Boolean)
                    .join(' ');

                  const label = studied
                    ? `${cell.date}: ${info?.total_minutes} minutes over ${info?.session_count} session${info?.session_count === 1 ? '' : 's'}`
                    : cell.date;

                  return (
                    <div
                      key={cell.date}
                      role="gridcell"
                      aria-label={label}
                      aria-selected={isSelected || undefined}
                      data-testid={`day-${cell.date}`}
                      data-studied={studied ? 'true' : undefined}
                      data-level={studied ? level : undefined}
                      className={className}
                      style={
                        studied
                          ? ({ '--cal-delay': `${delay}ms` } as CSSProperties)
                          : undefined
                      }
                      onClick={studied ? () => setSelected(cell.date) : undefined}
                      onKeyDown={
                        studied
                          ? (e) => {
                              if (e.key === 'Enter' || e.key === ' ') {
                                e.preventDefault();
                                setSelected(cell.date);
                              }
                            }
                          : undefined
                      }
                      tabIndex={studied ? 0 : undefined}
                    >
                      <span className="cal__daynum calendar__daynum">
                        {cell.day}
                      </span>
                      {studied && (
                        <>
                          <span className="cal__meta">
                            <span className="cal__dot calendar__dot" aria-hidden="true">
                              <DotIcon />
                            </span>
                            <span className="cal__minutes calendar__minutes">
                              {info?.total_minutes}m
                            </span>
                          </span>
                          <span className="cal__tip" role="tooltip">
                            {info?.total_minutes}m · {info?.session_count} session
                            {info?.session_count === 1 ? '' : 's'}
                          </span>
                        </>
                      )}
                    </div>
                  );
                })}
          </div>

          <div className="cal__legend" aria-hidden="true">
            <span>Less</span>
            <span className="cal__legend-swatch cal__legend-swatch--0" />
            <span className="cal__legend-swatch cal__legend-swatch--1" />
            <span className="cal__legend-swatch cal__legend-swatch--2" />
            <span className="cal__legend-swatch cal__legend-swatch--3" />
            <span className="cal__legend-swatch cal__legend-swatch--4" />
            <span>More</span>
          </div>
        </div>
      </Card>

      {selected && selectedDay && (
        <div className="cal__popover calendar__popover" role="status">
          <div className="cal__popover-head">
            <CalendarIcon size={16} />
            <strong>{selected}</strong>
          </div>
          <p className="cal__popover-meta muted">
            {selectedDay.total_minutes} minutes ·{' '}
            {selectedDay.session_count} session
            {selectedDay.session_count === 1 ? '' : 's'} ·{' '}
            {selectedDay.course_ids.length} course
            {selectedDay.course_ids.length === 1 ? '' : 's'}
          </p>
        </div>
      )}
    </div>
  );
}
