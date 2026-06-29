// TanStack Query hooks for courses, study sessions, stats and the calendar.
import {
  useMutation,
  useQuery,
  useQueryClient,
} from '@tanstack/react-query';
import { api } from '../../lib/api';
import type {
  CalendarResponse,
  Course,
  CourseCreate,
  CourseStatus,
  CourseUpdate,
  SessionCreate,
  Stats,
  StudySession,
} from '../../lib/types';

export const queryKeys = {
  courses: (status?: CourseStatus | 'all') => ['courses', status ?? 'all'] as const,
  course: (id: string) => ['course', id] as const,
  sessions: (courseId: string) => ['sessions', courseId] as const,
  calendar: (month: string) => ['calendar', month] as const,
  stats: () => ['stats'] as const,
};

export function useCourses(status?: CourseStatus | 'all') {
  return useQuery({
    queryKey: queryKeys.courses(status),
    queryFn: () => {
      const qs = status && status !== 'all' ? `?status=${status}` : '';
      return api.get<Course[]>(`/courses${qs}`);
    },
  });
}

export function useCreateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CourseCreate) =>
      api.post<Course>('/courses', body as unknown as Record<string, unknown>),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['courses'] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

export function useUpdateCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: CourseUpdate }) =>
      api.patch<Course>(
        `/courses/${id}`,
        body as unknown as Record<string, unknown>,
      ),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['courses'] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

export function useDeleteCourse() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.del<void>(`/courses/${id}`),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['courses'] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
      void qc.invalidateQueries({ queryKey: ['calendar'] });
    },
  });
}

export function useLogSession() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ courseId, body }: { courseId: string; body: SessionCreate }) =>
      api.post<StudySession>(
        `/courses/${courseId}/sessions`,
        body as unknown as Record<string, unknown>,
      ),
    onSuccess: (_data, vars) => {
      void qc.invalidateQueries({ queryKey: queryKeys.sessions(vars.courseId) });
      void qc.invalidateQueries({ queryKey: ['calendar'] });
      void qc.invalidateQueries({ queryKey: queryKeys.stats() });
    },
  });
}

export function useStats() {
  return useQuery({
    queryKey: queryKeys.stats(),
    queryFn: () => api.get<Stats>('/stats'),
  });
}

export function useCalendar(month: string) {
  return useQuery({
    queryKey: queryKeys.calendar(month),
    queryFn: () => api.get<CalendarResponse>(`/sessions/calendar?month=${month}`),
  });
}
