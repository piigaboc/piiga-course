import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Badge, StatusBadge } from './Badge';

describe('Badge', () => {
  it('defaults to the neutral variant', () => {
    render(<Badge>New</Badge>);
    expect(screen.getByText('New')).toHaveClass('badge', 'badge--neutral');
  });

  it('StatusBadge maps status to class + human label', () => {
    render(<StatusBadge status="in_progress" />);
    const el = screen.getByText('In progress');
    expect(el).toHaveClass('badge--in_progress');
  });
});
