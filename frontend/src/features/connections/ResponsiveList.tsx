/** A table from 640px up; stacked cards below it (UI.md §3). One column list drives both. */
import type { Key, ReactNode } from "react";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/states";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { cn } from "@/lib/utils";

export interface Column<T> {
  header: string;
  cell: (row: T) => ReactNode;
  /** Right-aligned tabular figures. */
  numeric?: boolean;
  /** Shown as the card's heading line instead of a "label: value" row. */
  primary?: boolean;
  /** Buttons: no header text, placed at the card's foot. */
  actions?: boolean;
}

interface ListProps<T> {
  rows: T[];
  rowKey: (row: T) => Key;
  columns: Column<T>[];
  caption: string;
}

export function ResponsiveList<T>({ rows, rowKey, columns, caption }: ListProps<T>) {
  const fields = columns.filter((c) => !c.primary && !c.actions);
  return (
    <>
      <div className="hidden rounded-lg border border-border bg-surface sm:block">
        <Table>
          <caption className="sr-only">{caption}</caption>
          <TableHeader>
            <TableRow>
              {columns.map((c) => (
                <TableHead key={c.header} className={cn(c.numeric && "text-right")}>
                  {c.actions ? <span className="sr-only">Actions</span> : c.header}
                </TableHead>
              ))}
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((row) => (
              <TableRow key={rowKey(row)}>
                {columns.map((c) => (
                  <TableCell key={c.header} className={cn(c.numeric && "tabular text-right", c.actions && "text-right")}>
                    {c.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
      <ul aria-label={caption} className="space-y-3 sm:hidden">
        {rows.map((row) => (
          <li key={rowKey(row)} className="space-y-2 rounded-lg border border-border bg-surface p-4">
            <div className="flex flex-wrap items-center justify-between gap-2 font-medium">
              {columns.filter((c) => c.primary).map((c) => (
                <span key={c.header}>{c.cell(row)}</span>
              ))}
            </div>
            <dl className="space-y-1 text-sm">
              {fields.map((c) => (
                <div key={c.header} className="flex justify-between gap-3">
                  <dt className="text-text-muted">{c.header}</dt>
                  <dd className={cn("text-right", c.numeric && "tabular")}>{c.cell(row)}</dd>
                </div>
              ))}
            </dl>
            {columns.filter((c) => c.actions).map((c) => (
              <div key={c.header} className="flex flex-wrap justify-end gap-2 pt-1">
                {c.cell(row)}
              </div>
            ))}
          </li>
        ))}
      </ul>
    </>
  );
}

interface BoundaryProps {
  query: { isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown };
  isEmpty: boolean;
  emptyTitle: string;
  emptyHint?: ReactNode;
  children: ReactNode;
}

/** Loading skeleton, error with Retry and request id, or the empty message; otherwise the list. */
export function ListBoundary({ query, isEmpty, emptyTitle, emptyHint, children }: BoundaryProps) {
  if (query.isPending) return <LoadingBlock lines={5} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => void query.refetch()} />;
  if (isEmpty) return <EmptyState title={emptyTitle}>{emptyHint}</EmptyState>;
  return <>{children}</>;
}
