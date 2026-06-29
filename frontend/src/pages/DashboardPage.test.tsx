import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen } from '@testing-library/react';
import { DashboardPage } from './DashboardPage';
import { renderWithProviders, jsonResponse } from '../test/renderWithProviders';
import type { Course, Stats } from '../lib/types';

const STATS: Stats = {
  active_courses: 3,
  completed_courses: 1,
  total_courses: 5,
  total_minutes: 600,
  total_hours: 10,
  current_streak: 4,
  sessions_this_week: 7,
};

const IN_PROGRESS: Course[] = [
  {
    id: 'c1',
    title: 'Distributed Systems',
    platform: 'MIT OCW',
    url: 'https://example.com/ds',
    status: 'in_progress',
    target_date: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
  },
];

describe('DashboardPage', () => {
  beforeEach(() => vi.restoreAllMocks());
  afterEach(() => vi.restoreAllMocks());

  it('renders stat tiles and the in-progress course list', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/stats')) return Promise.resolve(jsonResponse(STATS));
      if (url.includes('status=in_progress')) {
        return Promise.resolve(jsonResponse(IN_PROGRESS));
      }
      return Promise.reject(new Error(`unexpected ${url}`));
    });

    renderWithProviders(<DashboardPage />);

    // Tiles.
    expect(await screen.findByText('Active courses')).toBeInTheDocument();
    expect(screen.getByText('3')).toBeInTheDocument();
    expect(screen.getByText('Total hours')).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
    expect(screen.getByText('Current streak')).toBeInTheDocument();
    expect(screen.getByText('Sessions this week')).toBeInTheDocument();
    expect(screen.getByText('7')).toBeInTheDocument();

    // In-progress list.
    expect(
      await screen.findByText('Distributed Systems'),
    ).toBeInTheDocument();
    expect(screen.getByText('MIT OCW')).toBeInTheDocument();
  });
});
