import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { TableSkeleton } from "./LoadingSkeleton";
import { EmptyState } from "./EmptyState";

export interface Column<T> {
  key: string;
  header: string;
  render?: (item: T) => React.ReactNode;
  className?: string;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  isLoading?: boolean;
  emptyTitle?: string;
  emptyDescription?: string;
  currentPage?: number;
  totalPages?: number;
  totalItems?: number;
  onPageChange?: (page: number) => void;
  onRowClick?: (item: T) => void;
}

export function DataTable<T extends { id?: string | number }>({
  columns,
  data,
  isLoading,
  emptyTitle = "Nothing here yet",
  emptyDescription = "No records match the current filters.",
  currentPage = 1,
  totalPages = 1,
  totalItems,
  onPageChange,
  onRowClick,
}: DataTableProps<T>) {
  if (isLoading) return <TableSkeleton rows={6} />;
  if (!data || data.length === 0)
    return <EmptyState title={emptyTitle} description={emptyDescription} />;

  return (
    <div>
      <div className="surface-card overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full border-collapse text-left text-sm">
            <thead>
              <tr className="border-b border-line bg-elevated">
                {columns.map((col) => (
                  <th
                    key={col.key}
                    className={`whitespace-nowrap px-4 py-2.5 text-xs font-semibold text-text-2 ${
                      col.className || ""
                    }`}
                  >
                    {col.header}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.map((item, idx) => (
                <tr
                  key={item.id || idx}
                  onClick={() => onRowClick?.(item)}
                  className={`border-b border-line last:border-b-0 ${
                    onRowClick ? "cursor-pointer hover:bg-elevated" : "hover:bg-elevated"
                  }`}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      className={`px-4 py-3 align-middle text-text-1 ${col.className || ""}`}
                    >
                      {col.render ? col.render(item) : (item as any)[col.key]}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {totalPages > 1 && onPageChange && (
        <div className="mt-3 flex items-center justify-between text-sm text-text-2">
          <span>
            Page {currentPage} of {totalPages}
            {typeof totalItems === "number" ? ` · ${totalItems} total` : ""}
          </span>
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => onPageChange(currentPage - 1)}
              disabled={currentPage <= 1}
              className="inline-flex items-center gap-1 rounded-lg border border-line bg-card px-2.5 py-1.5 font-medium text-text-1 hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40"
            >
              <ChevronLeft size={14} /> Previous
            </button>
            <button
              onClick={() => onPageChange(currentPage + 1)}
              disabled={currentPage >= totalPages}
              className="inline-flex items-center gap-1 rounded-lg border border-line bg-card px-2.5 py-1.5 font-medium text-text-1 hover:bg-elevated disabled:cursor-not-allowed disabled:opacity-40"
            >
              Next <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
