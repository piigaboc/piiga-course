import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';

export interface ModalProps {
  open: boolean;
  onClose: () => void;
  title?: ReactNode;
  description?: ReactNode;
  children?: ReactNode;
  /** Optional footer (e.g. action buttons). */
  footer?: ReactNode;
}

/**
 * Stone-styled accessible modal dialog.
 * - Renders into document.body via a portal.
 * - Closes on Escape and on backdrop click.
 * - Traps initial focus on the panel; restores focus to the opener on close.
 */
export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: ModalProps) {
  const panelRef = useRef<HTMLDivElement>(null);
  const titleId = useId();
  const descId = useId();
  const lastFocused = useRef<Element | null>(null);
  // Keep the latest onClose without making it an effect dependency, so the
  // focus/scroll-lock effect only runs when `open` actually toggles (otherwise
  // an inline onClose prop re-runs it on every keystroke and steals focus).
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!open) return;
    lastFocused.current = document.activeElement;

    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') onCloseRef.current();
    }
    document.addEventListener('keydown', onKey);

    // Focus the panel for screen readers / keyboard users.
    panelRef.current?.focus();

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', onKey);
      document.body.style.overflow = prevOverflow;
      if (lastFocused.current instanceof HTMLElement) {
        lastFocused.current.focus();
      }
    };
  }, [open]);

  if (!open) return null;

  return createPortal(
    <div
      className="modal__backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        ref={panelRef}
        className="modal__panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby={title != null ? titleId : undefined}
        aria-describedby={description != null ? descId : undefined}
        tabIndex={-1}
      >
        {(title != null || description != null) && (
          <div className="modal__header">
            {title != null && (
              <h2 id={titleId} className="modal__title">
                {title}
              </h2>
            )}
            {description != null && (
              <p id={descId} className="modal__description">
                {description}
              </p>
            )}
          </div>
        )}
        <div className="modal__body">{children}</div>
        {footer != null && <div className="modal__footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}
