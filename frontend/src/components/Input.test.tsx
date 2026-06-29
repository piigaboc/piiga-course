import { describe, expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Input } from './Input';

describe('Input', () => {
  it('associates label and renders value', () => {
    render(<Input label="Email" value="a@b.com" onChange={() => {}} />);
    expect(screen.getByLabelText('Email')).toHaveValue('a@b.com');
  });

  it('exposes error state via aria and class', () => {
    render(<Input label="Email" error="Required" onChange={() => {}} />);
    const input = screen.getByLabelText('Email');
    expect(input).toHaveClass('input--error');
    expect(input).toHaveAttribute('aria-invalid', 'true');
    expect(input).toHaveAccessibleDescription('Required');
  });
});
