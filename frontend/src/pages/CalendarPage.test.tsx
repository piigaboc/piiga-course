import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CalendarPage } from './CalendarPage';
import { renderWithProviders, jsonResponse } from '../test/renderWithProviders';

describe('CalendarPage', () => {
  beforeEach(() => {
    // Pin "today" so the rendered month is deterministic. shouldAdvanceTime
    // keeps Testing Library's findBy* polling and userEvent working.
    vi.useFakeTimers({ shouldAdvanceTime: true });
    vi.setSystemTime(new Date('2026-06-15T12:00:00Z'));
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  function mockCalendar() {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/sessions/calendar')) {
        return Promise.resolve(
          jsonResponse({
            month: '2026-06',
            days: [
              {
                date: '2026-06-10',
                total_minutes: 45,
                session_count: 2,
                course_ids: ['c1'],
              },
            ],
          }),
        );
      }
      return Promise.reject(new Error(`unexpected ${url}`));
    });
  }

  it('renders the Thai subtitle and the studied day highlight', async () => {
    mockCalendar();
    renderWithProviders(<CalendarPage />);

    expect(screen.getByText(/เรียนวันไหนบ้าง/)).toBeInTheDocument();

    const studied = await screen.findByTestId('day-2026-06-10');
    await waitFor(() =>
      expect(studied).toHaveClass('calendar__cell--studied'),
    );
    expect(studied).toHaveAttribute('data-studied', 'true');
    expect(studied).toHaveTextContent('45m');

    // A day with no sessions is not highlighted.
    expect(screen.getByTestId('day-2026-06-11')).not.toHaveClass(
      'calendar__cell--studied',
    );
  });

  it('shows a popover with totals when a studied day is clicked', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
    mockCalendar();
    renderWithProviders(<CalendarPage />);

    const studied = await screen.findByTestId('day-2026-06-10');
    await waitFor(() =>
      expect(studied).toHaveClass('calendar__cell--studied'),
    );

    await user.click(studied);

    expect(await screen.findByRole('status')).toHaveTextContent(
      /45 minutes/,
    );
  });
});
