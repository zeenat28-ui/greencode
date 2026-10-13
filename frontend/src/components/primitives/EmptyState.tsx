import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

export interface EmptyStateProps extends React.HTMLAttributes<HTMLDivElement> {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg';
}

const sizeClasses: Record<NonNullable<EmptyStateProps['size']>, string> = {
  sm: 'py-6',
  md: 'py-10',
  lg: 'py-16',
};

export const EmptyState = forwardRef<HTMLDivElement, EmptyStateProps>(
  ({ className, icon, title, description, action, size = 'md', ...props }, ref) => (
    <div
      ref={ref}
      className={cn(
        'flex flex-col items-center justify-center text-center',
        sizeClasses[size],
        className
      )}
      {...props}
    >
      {icon && <div className="mb-3 text-zinc-400">{icon}</div>}
      <h3 className="text-sm font-semibold text-zinc-900 mb-1">{title}</h3>
      {description && (
        <p className="text-xs text-zinc-500 mb-4 max-w-md leading-relaxed">{description}</p>
      )}
      {action}
    </div>
  )
);
EmptyState.displayName = 'EmptyState';
