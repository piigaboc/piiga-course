import type { HTMLAttributes, ReactNode } from 'react';
import type { CourseStatus } from '../lib/types';

export type BadgeVariant = 'neutral' | 'accent' | CourseStatus;

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  children: ReactNode;
}

const STATUS_LABELS: Record<CourseStatus, string> = {
  planned: 'Planned',
  in_progress: 'In progress',
  completed: 'Completed',
  paused: 'Paused',
};

function cx(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

export function Badge({
  variant = 'neutral',
  className,
  children,
  ...rest
}: BadgeProps) {
  return (
    <span className={cx('badge', `badge--${variant}`, className)} {...rest}>
      {children}
    </span>
  );
}

/** Status badge with the canonical human label (always pairs color + text). */
export function StatusBadge({
  status,
  ...rest
}: { status: CourseStatus } & Omit<BadgeProps, 'variant' | 'children'>) {
  return (
    <Badge variant={status} {...rest}>
      {STATUS_LABELS[status]}
    </Badge>
  );
}
