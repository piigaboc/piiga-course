import type { HTMLAttributes, ReactNode } from 'react';

export interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, 'title'> {
  title?: ReactNode;
  description?: ReactNode;
  raised?: boolean;
  /**
   * Render a terminal-style title bar (red/amber/green window dots + a
   * monospace ~/path string) at the top of the card. When set, the card
   * becomes a padding-less panel; wrap content padding with the `term-body`
   * helper or your own element. Optional `titleBarMeta` shows a muted string
   * on the right (e.g. `12 total`).
   */
  titleBar?: ReactNode;
  titleBarMeta?: ReactNode;
  children?: ReactNode;
}

function cx(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

export function Card({
  title,
  description,
  raised,
  titleBar,
  titleBarMeta,
  className,
  children,
  ...rest
}: CardProps) {
  if (titleBar != null) {
    return (
      <div
        className={cx('card', 'term-panel', raised && 'card--raised', className)}
        {...rest}
      >
        <div className="term-titlebar">
          <span className="term-titlebar__path">
            <span className="term-dots" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <span>{titleBar}</span>
          </span>
          {titleBarMeta != null && (
            <span className="term-titlebar__meta">{titleBarMeta}</span>
          )}
        </div>
        {children}
      </div>
    );
  }

  return (
    <div className={cx('card', raised && 'card--raised', className)} {...rest}>
      {title != null && <h3 className="card__title">{title}</h3>}
      {description != null && <p className="card__description">{description}</p>}
      {children}
    </div>
  );
}
