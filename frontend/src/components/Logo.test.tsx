import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Logo } from './Logo';

describe('Logo', () => {
  it('renders an accessible image mark by default', () => {
    render(<Logo />);
    const mark = screen.getByRole('img', { name: 'PiigaCourse' });
    expect(mark).toBeInTheDocument();
    // currentColor / token-driven: no hard-coded hex on the mark.
    expect(mark.getAttribute('width')).toBe('28');
  });

  it('respects the size prop', () => {
    render(<Logo size={44} />);
    const mark = screen.getByRole('img', { name: 'PiigaCourse' });
    expect(mark.getAttribute('width')).toBe('44');
    expect(mark.getAttribute('height')).toBe('44');
  });

  it('shows the wordmark and hides the decorative icon from a11y tree', () => {
    const { container } = render(<Logo withWordmark />);
    expect(screen.getByText('PiigaCourse')).toBeInTheDocument();
    // With a visible wordmark the svg becomes decorative (aria-hidden).
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe(
      'true',
    );
    expect(screen.queryByRole('img')).not.toBeInTheDocument();
  });

  it('adds the animation class only when animated', () => {
    const { container, rerender } = render(<Logo />);
    expect(container.querySelector('.logo__mark--animated')).toBeNull();
    rerender(<Logo animated />);
    expect(container.querySelector('.logo__mark--animated')).not.toBeNull();
  });
});
