import type { ReactNode } from 'react';

export interface StatTileProps {
  label: ReactNode;
  value: ReactNode;
  /** Optional small caption under the value (e.g. units, context). */
  hint?: ReactNode;
  /** Optional decorative icon glyph shown in a tinted square. */
  icon?: ReactNode;
  /**
   * Use the green activity/success accent (icon chip + value ink).
   * Reserve for study/streak/activity tiles — not a global default.
   */
  accent?: boolean;
  /** Optional className for layout/animation hooks (e.g. stagger delay). */
  className?: string;
  style?: React.CSSProperties;
}

function cx(...parts: Array<string | false | undefined>): string {
  return parts.filter(Boolean).join(' ');
}

/**
 * Dashboard metric tile: big monospace/tabular number + label, in a stone
 * Card surface. `accent` swaps the icon chip + number to the green activity
 * accent. Consumes theme + nerd tokens only (see THEME.md "StatTile").
 */
export function StatTile({
  label,
  value,
  hint,
  icon,
  accent,
  className,
  style,
}: StatTileProps) {
  return (
    <div
      className={cx('stat-tile', accent && 'stat-tile--accent', className)}
      style={style}
    >
      {icon != null && (
        <span className="stat-tile__icon" aria-hidden="true">
          {icon}
        </span>
      )}
      <div className="stat-tile__body">
        <div className="stat-tile__value mono">{value}</div>
        <div className="stat-tile__label">{label}</div>
        {hint != null && <div className="stat-tile__hint mono">{hint}</div>}
      </div>
    </div>
  );
}
