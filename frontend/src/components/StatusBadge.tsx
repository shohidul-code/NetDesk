/** Status is a word plus a colour, never colour alone (UI.md §2, §5). */
import { cn } from "@/lib/utils";

const TONE: Record<string, string> = {
  paid: "bg-success/10 text-success",
  active: "bg-success/10 text-success",
  resolved: "bg-success/10 text-success",
  closed: "bg-success/10 text-success",
  waived: "bg-success/10 text-success",
  unpaid: "bg-warning/10 text-warning",
  open: "bg-warning/10 text-warning",
  in_progress: "bg-warning/10 text-warning",
  maintenance: "bg-warning/10 text-warning",
  suspended: "bg-danger/10 text-danger",
  disconnected: "bg-danger/10 text-danger",
  outage: "bg-danger/10 text-danger",
};

const LABEL: Record<string, string> = { in_progress: "In progress" };

export function StatusBadge({ status }: { status: string }) {
  const label = LABEL[status] ?? status.charAt(0).toUpperCase() + status.slice(1).replace(/_/g, " ");
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        TONE[status] ?? "bg-bg text-text-muted",
      )}
    >
      {label}
    </span>
  );
}
