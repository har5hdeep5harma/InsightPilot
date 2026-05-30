import type { DatasetColumn } from "@/types/api";

type DataPreviewTableProps = {
  columns: DatasetColumn[];
  rows: Record<string, unknown>[];
};

export function DataPreviewTable({ columns, rows }: DataPreviewTableProps) {
  const visibleColumns = columns.slice(0, 8);

  return (
    <div className="overflow-hidden rounded-lg border bg-surface">
      <div className="max-h-[420px] overflow-auto">
        <table className="w-full min-w-[720px] border-collapse text-left text-body-sm">
          <thead className="sticky top-0 bg-surface-raised">
            <tr>
              {visibleColumns.map((column) => (
                <th
                  key={column.name}
                  className="border-b px-4 py-3 font-medium text-muted-foreground"
                >
                  {column.original_name || column.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex} className="border-b last:border-b-0">
                {visibleColumns.map((column) => (
                  <td key={column.name} className="max-w-48 truncate px-4 py-3 text-foreground">
                    {formatCell(row[column.name])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {columns.length > visibleColumns.length ? (
        <div className="border-t bg-surface-raised px-4 py-2 text-caption text-muted-foreground">
          Showing {visibleColumns.length} of {columns.length} columns.
        </div>
      ) : null}
    </div>
  );
}

function formatCell(value: unknown) {
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}
