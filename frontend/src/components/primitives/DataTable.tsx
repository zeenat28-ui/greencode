import { cn } from '../../lib/utils';
import { translateStatic } from '../../i18n/I18nContext';

export type ColumnAlign = 'left' | 'center' | 'right';

export interface ColumnDef<T> {
  key: string;
  header: React.ReactNode;
  cell: ((row: T) => React.ReactNode) | ((row: T) => React.ReactNode);
  align?: ColumnAlign;
  className?: string;
  headerClassName?: string;
  sortable?: boolean;
}

export interface DataTableProps<T> {
  columns: ColumnDef<T>[];
  data: T[];
  keyField?: keyof T | ((row: T) => string);
  emptyMessage?: string;
  emptyIcon?: React.ReactNode;
  loading?: boolean;
  striped?: boolean;
  hover?: boolean;
  className?: string;
  rowClassName?: (row: T) => string;
  headerClassName?: string;
  noPadding?: boolean;
}

function getRowKey<T>(row: T, keyField: NonNullable<DataTableProps<T>['keyField']>, index: number): string {
  if (typeof keyField === 'function') return String(keyField(row));
  const val = row[keyField];
  return val != null ? String(val) : `row-${index}`;
}

export function DataTable<T extends Record<string, unknown>>({
  columns,
  data,
  keyField = 'id' as keyof T,
  emptyMessage = translateStatic('empty.noData'),
  emptyIcon,
  loading = false,
  striped = true,
  hover = true,
  className,
  rowClassName,
  headerClassName,
  noPadding = false,
}: DataTableProps<T>) {
  const pad = noPadding ? 'p-0' : 'px-5 py-3.5';

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-10 bg-[var(--gc-bg-subtle)] border-b border-[var(--gc-border-default)] rounded-t-lg" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-[var(--gc-bg-default)] border-b border-[var(--gc-border-subtle)]" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-8 text-[var(--gc-text-tertiary)]">
        {emptyIcon && <div className="mb-3 flex justify-center">{emptyIcon}</div>}
        <p className="text-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-x-auto rounded-lg border border-[var(--gc-border-default)] bg-[var(--gc-bg-default)]',
        className
      )}
    >
      <table className="w-full text-left text-sm">
        <thead className={cn('bg-[var(--gc-bg-subtle)] text-[var(--gc-text-tertiary)] uppercase', headerClassName)}>
          <tr>
            {columns.map((col) => (
              <th
                key={col.key}
                className={cn(
                  'px-3 py-3 font-medium text-[10px] uppercase tracking-wider',
                  col.headerClassName
                )}
                style={{ textAlign: col.align ?? 'left' }}
              >
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr
              key={getRowKey(row, keyField, i)}
              className={cn(
                striped && i % 2 === 1 && 'bg-[var(--gc-bg-subtle)]/50',
                hover && 'hover:bg-[var(--gc-row-hover)]',
                rowClassName?.(row)
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(pad, 'text-[var(--gc-text-primary)] align-top')}
                  style={{ textAlign: col.align ?? 'left' }}
                >
                  {typeof col.cell === 'function' ? col.cell(row) : col.cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
