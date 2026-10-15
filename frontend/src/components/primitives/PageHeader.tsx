import { forwardRef } from 'react';
import { cn } from '../../lib/utils';
import { ChevronLeft, ChevronRight } from 'lucide-react';

export interface PageHeaderProps extends Omit<React.HTMLAttributes<HTMLElement>, 'title'> {
  title: React.ReactNode;
  description?: React.ReactNode;
  action?: React.ReactNode;
  breadcrumbs?: Array<{ label: string; href?: string }>;
  backHref?: string;
  backLabel?: string;
}

export const PageHeader = forwardRef<HTMLElement, PageHeaderProps>(
  (
    { className, title, description, action, breadcrumbs, backHref, backLabel, ...props },
    ref
  ) => {
    return (
      <header
        ref={ref}
        className={cn(
          'flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 pb-2 border-b border-[var(--gc-border-default)]',
          className
        )}
        {...props}
      >
        <div className="min-w-0 flex-1">
          {breadcrumbs && breadcrumbs.length > 0 && (
            <nav aria-label="Breadcrumb" className="mb-1">
              <ol className="flex items-center gap-1.5 text-[11px] font-mono text-zinc-400">
                {breadcrumbs.map((crumb, i) => (
                  <li key={i} className="flex items-center gap-1.5">
                    {i > 0 && <span className="text-zinc-300">/</span>}
                    {crumb.href ? (
                      <a
                        href={crumb.href}
                        className="text-zinc-500 hover:text-zinc-900 transition-colors"
                      >
                        {crumb.label}
                      </a>
                    ) : (
                      <span className="text-zinc-900 font-medium">{crumb.label}</span>
                    )}
                  </li>
                ))}
              </ol>
            </nav>
          )}
          <h1 className="text-base font-semibold text-[var(--gc-text-primary)] tracking-tight truncate">
            {title}
          </h1>
          {description && (
            <p className="text-xs text-[var(--gc-text-tertiary)] mt-0.5 truncate">
              {description}
            </p>
          )}
        </div>
        {action && <div className="shrink-0">{action}</div>}
      </header>
    );
  }
);
PageHeader.displayName = 'PageHeader';

export { ChevronLeft, ChevronRight };
