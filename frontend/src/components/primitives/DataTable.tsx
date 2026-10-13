import { forwardRef } from 'react';
import { cn } from '../../lib/utils';

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
  emptyMessage = 'No data to display.',
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
        <div className="h-10 bg-zinc-100 border-b border-zinc-200 rounded-t-lg" />
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-12 bg-zinc-50 border-b border-zinc-100" />
        ))}
      </div>
    );
  }

  if (data.length === 0) {
    return (
      <div className="text-center py-10 text-zinc-500">
        {emptyIcon && <div className="mb-3 flex justify-center">{emptyIcon}</div>}
        <p className="text-sm">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div
      className={cn(
        'overflow-x-auto rounded-xl border border-zinc-200/80 bg-white',
        'divide-y divide-zinc-100',
        className
      )}
    >
      <table className="w-full text-left text-sm">
        <thead className={cn('bg-zinc-50 text-zinc-500 uppercase', headerClassName)}>
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
                striped && i % 2 === 1 && 'bg-zinc-50/50',
                hover && 'hover:bg-zinc-50/80',
                rowClassName?.(row)
              )}
            >
              {columns.map((col) => (
                <td
                  key={col.key}
                  className={cn(pad, 'text-zinc-900 align-top')}
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
