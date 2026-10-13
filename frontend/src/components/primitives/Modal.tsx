import { forwardRef, useEffect } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { cn } from '../../lib/utils';

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: React.ReactNode;
  children: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl' | 'full';
  showCloseButton?: boolean;
  closeOnEscape?: boolean;
  closeOnOverlayClick?: boolean;
  className?: string;
  overlayClassName?: string;
  contentClassName?: string;
  footer?: React.ReactNode;
}

const sizeClasses: Record<NonNullable<ModalProps['size']>, string> = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
  full: 'max-w-[90vw] max-h-[90vh]',
};

export const Modal = forwardRef<HTMLDivElement, ModalProps>(
  (
     {
       isOpen,
       onClose,
       title,
       children,
       size = 'md',
       showCloseButton = true,
       closeOnEscape = true,
       closeOnOverlayClick = true,
       className,
       overlayClassName,
       contentClassName,
       footer,
     },
    _ref
  ) => {
    useEffect(() => {
      if (!isOpen || !closeOnEscape) return;
      const onKey = (e: KeyboardEvent) => {
        if (e.key === 'Escape') onClose();
      };
      document.addEventListener('keydown', onKey);
      return () => document.removeEventListener('keydown', onKey);
    }, [isOpen, onClose, closeOnEscape]);

    useEffect(() => {
      if (isOpen) {
        document.body.style.overflow = 'hidden';
        return () => {
          document.body.style.overflow = '';
        };
      }
    }, [isOpen]);

    if (!isOpen) return null;

    const overlayClick = (e: React.MouseEvent) => {
      if (closeOnOverlayClick && e.target === e.currentTarget) onClose();
    };

    const content = (
      <div
        className={cn(
          'fixed inset-0 z-50 overflow-y-auto bg-black/60 backdrop-blur-sm flex items-start justify-center p-4',
          overlayClassName
        )}
        onClick={overlayClick}
      >
        <div
          className={cn(
            'bg-white rounded-xl shadow-2xl border border-zinc-200 w-full my-6',
            'animate-fade-in',
            sizeClasses[size],
            className
          )}
          onClick={(e) => e.stopPropagation()}
        >
          {(title || showCloseButton) && (
            <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-200/80">
              {title && <h3 className="text-sm font-semibold text-zinc-950">{title}</h3>}
              {showCloseButton && (
                <button
                  onClick={onClose}
                  type="button"
                  className="p-1 rounded text-zinc-500 hover:text-zinc-900 hover:bg-zinc-100 transition-colors"
                  aria-label="Close"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          )}
          <div className={cn('p-6 overflow-y-auto', contentClassName)} style={{ maxHeight: 'calc(90vh - 180px)' }}>
            {children}
          </div>
          {footer && <div className="px-6 py-4 border-t border-zinc-200/80 bg-zinc-50/50">{footer}</div>}
        </div>
      </div>
    );

    return createPortal(content, document.body);
  }
);
Modal.displayName = 'Modal';
