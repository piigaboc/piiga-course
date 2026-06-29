import { forwardRef, useId, type InputHTMLAttributes, type ReactNode } from 'react';

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: ReactNode;
  hint?: ReactNode;
  error?: ReactNode;
}

function cx(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ label, hint, error, id, className, ...rest }, ref) => {
    const autoId = useId();
    const inputId = id ?? autoId;
    const hintId = `${inputId}-hint`;
    const hasError = Boolean(error);
    const message = error ?? hint;

    return (
      <div className="field">
        {label != null && (
          <label className="field__label" htmlFor={inputId}>
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          className={cx('input', hasError && 'input--error', className)}
          aria-invalid={hasError || undefined}
          aria-describedby={message != null ? hintId : undefined}
          {...rest}
        />
        {message != null && (
          <span
            id={hintId}
            className={cx('field__hint', hasError && 'field__hint--error')}
          >
            {message}
          </span>
        )}
      </div>
    );
  },
);
Input.displayName = 'Input';
