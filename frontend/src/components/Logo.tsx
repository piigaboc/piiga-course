import type { SVGProps } from 'react';

export interface LogoProps {
  /** Pixel size of the square SVG mark. Defaults to 28. */
  size?: number;
  /** Render the "PiigaCourse" wordmark next to the icon. */
  withWordmark?: boolean;
  /**
   * Enable the gentle draw-in / idle animation on the mark.
   * Animation is decorative and is suppressed under prefers-reduced-motion.
   */
  animated?: boolean;
  /** Accessible label. Ignored (mark becomes decorative) when withWordmark is set. */
  title?: string;
  className?: string;
}

/**
 * PiigaCourse brand mark — a stacked open-book / progress motif:
 * three ascending "pages" (a learning-progress staircase) cradled by an open
 * book base, with an accent check spark. Drawn entirely with `currentColor`
 * and stone tokens so it inherits text/accent colors and adapts to dark mode.
 */
export function Logo({
  size = 28,
  withWordmark = false,
  animated = false,
  title = 'PiigaCourse',
  className,
}: LogoProps) {
  const labelled = !withWordmark;
  const svgProps: SVGProps<SVGSVGElement> = labelled
    ? { role: 'img', 'aria-label': title }
    : { 'aria-hidden': true, focusable: false };

  return (
    <span
      className={['logo', withWordmark && 'logo--wordmark', className]
        .filter(Boolean)
        .join(' ')}
    >
      <svg
        width={size}
        height={size}
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className={['logo__mark', animated && 'logo__mark--animated']
          .filter(Boolean)
          .join(' ')}
        {...svgProps}
      >
        {/* Open-book base */}
        <path
          className="logo__book"
          d="M4 23.5C7 21.5 10 21.5 13 23.5C13 23.5 13 12 13 12C10 10 7 10 4 12C4 12 4 23.5 4 23.5Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        <path
          className="logo__book"
          d="M28 23.5C25 21.5 22 21.5 19 23.5C19 23.5 19 12 19 12C22 10 25 10 28 12C28 12 28 23.5 28 23.5Z"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinejoin="round"
        />
        {/* Ascending progress pages (staircase) */}
        <rect
          className="logo__step logo__step--1"
          x="13"
          y="17"
          width="3.2"
          height="6"
          rx="1"
          fill="currentColor"
        />
        <rect
          className="logo__step logo__step--2"
          x="14.4"
          y="13"
          width="3.2"
          height="10"
          rx="1"
          fill="currentColor"
        />
        <rect
          className="logo__step logo__step--3"
          x="15.8"
          y="9"
          width="3.2"
          height="14"
          rx="1"
          fill="currentColor"
        />
        {/* Accent spark */}
        <circle
          className="logo__spark"
          cx="24.5"
          cy="7.5"
          r="2"
          fill="var(--accent)"
        />
      </svg>
      {withWordmark && <span className="logo__wordmark">PiigaCourse</span>}
    </span>
  );
}
