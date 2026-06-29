import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { CoursesPage } from './CoursesPage';
import { renderWithProviders, jsonResponse } from '../test/renderWithProviders';
import type { Course } from '../lib/types';

function course(over: Partial<Course>): Course {
  return {
    id: 'c1',
    title: 'React',
    platform: 'Udemy',
    url: 'https://example.com/react',
    status: 'in_progress',
    target_date: null,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-01T00:00:00Z',
    ...over,
  };
}

const ALL = [
  course({ id: 'c1', title: 'React', status: 'in_progress' }),
  course({
    id: 'c2',
    title: 'Go',
    status: 'planned',
    platform: 'Coursera',
    url: 'https://example.com/go',
  }),
];

describe('CoursesPage', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });
  afterEach(() => vi.restoreAllMocks());

  it('lists courses with title, platform, link and status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation((input) => {
      const url = String(input);
      if (url.includes('/courses')) return Promise.resolve(jsonResponse(ALL));
      return Promise.reject(new Error(`unexpected ${url}`));
    });

    renderWithProviders(<CoursesPage />);

    expect(await screen.findByText('React')).toBeInTheDocument();
    expect(screen.getByText('Go')).toBeInTheDocument();
    const link = screen.getByRole('link', {
      name: 'https://example.com/react',
    });
    expect(link).toHaveAttribute('target', '_blank');
    expect(screen.getByText('Udemy')).toBeInTheDocument();
  });

  it('filters by status, requesting the status query param', async () => {
    const fetchMock = vi
      .spyOn(globalThis, 'fetch')
      .mockImplementation((input) => {
        const url = String(input);
        if (url.includes('status=planned')) {
          return Promise.resolve(jsonResponse([ALL[1]]));
        }
        if (url.includes('/courses')) {
          return Promise.resolve(jsonResponse(ALL));
        }
        return Promise.reject(new Error(`unexpected ${url}`));
      });

    renderWithProviders(<CoursesPage />);
    await screen.findByText('React');

    await userEvent.click(screen.getByRole('button', { name: 'Planned' }));

    await waitFor(() => expect(screen.queryByText('React')).toBeNull());
    expect(screen.getByText('Go')).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some(([u]) =>
        String(u).includes('status=planned'),
      ),
    ).toBe(true);
  });

  it('adds a course via the modal and POSTs the payload', async () => {
    const posted: unknown[] = [];
    vi.spyOn(globalThis, 'fetch').mockImplementation((input, init) => {
      const url = String(input);
      const method = (init?.method ?? 'GET').toUpperCase();
      if (url.includes('/courses') && method === 'POST') {
        posted.push(JSON.parse(String(init?.body)));
        return Promise.resolve(
          jsonResponse(course({ id: 'c3', title: 'Rust', status: 'planned' })),
        );
      }
      if (url.includes('/courses')) return Promise.resolve(jsonResponse(ALL));
      return Promise.reject(new Error(`unexpected ${url}`));
    });

    const user = userEvent.setup();
    renderWithProviders(<CoursesPage />);
    await screen.findByText('React');

    await user.click(screen.getByRole('button', { name: 'Add course' }));

    const dialog = await screen.findByRole('dialog');
    await user.type(within(dialog).getByLabelText('Title'), 'Rust');
    await user.type(within(dialog).getByLabelText('Platform'), 'The Book');
    await user.click(
      within(dialog).getByRole('button', { name: 'Add course' }),
    );

    await waitFor(() => expect(posted).toHaveLength(1));
    expect(posted[0]).toMatchObject({
      title: 'Rust',
      platform: 'The Book',
      status: 'planned',
    });
  });
});
