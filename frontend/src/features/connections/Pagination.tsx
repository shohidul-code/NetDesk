import { Button } from "@/components/ui/button";

interface Props {
  total: number;
  limit: number;
  offset: number;
  onChange: (offset: number) => void;
}

export function Pagination({ total, limit, offset, onChange }: Props) {
  if (total === 0) return null;
  const from = offset + 1;
  const to = Math.min(offset + limit, total);
  return (
    <nav aria-label="Pages" className="mt-4 flex items-center justify-between gap-3">
      <p className="tabular text-sm text-text-muted">
        {from}–{to} of {total}
      </p>
      <div className="flex gap-2">
        <Button variant="outline" className="h-11" disabled={offset === 0} onClick={() => onChange(Math.max(0, offset - limit))}>
          Previous
        </Button>
        <Button variant="outline" className="h-11" disabled={offset + limit >= total} onClick={() => onChange(offset + limit)}>
          Next
        </Button>
      </div>
    </nav>
  );
}
