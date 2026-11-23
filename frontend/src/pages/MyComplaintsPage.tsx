import { EmptyState, ErrorState, LoadingBlock, PageHeader } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ComplaintForm } from "@/features/my-complaints/ComplaintForm";
import { categoryLabel } from "@/features/my-complaints/labels";
import { useComplaints } from "@/features/my-complaints/queries";
import { formatDateTime } from "@/lib/format";

export function MyComplaintsPage() {
  const complaints = useComplaints();

  let list;
  if (complaints.isPending) list = <LoadingBlock />;
  else if (complaints.isError) list = <ErrorState error={complaints.error} onRetry={() => void complaints.refetch()} />;
  else if (complaints.data.length === 0) list = <EmptyState title="No complaints yet" />;
  else
    list = (
      <ul className="divide-y divide-border rounded-lg border border-border bg-surface">
        {complaints.data.map((c) => (
          <li key={c.id} className="flex items-start justify-between gap-3 p-4">
            <div className="min-w-0">
              <p className="font-medium">{categoryLabel(c.category)}</p>
              <p className="text-sm text-text-muted">{formatDateTime(c.created_at)}</p>
              <p className="mt-1 break-words text-sm">{c.description}</p>
            </div>
            <StatusBadge status={c.status} />
          </li>
        ))}
      </ul>
    );

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <PageHeader title="My complaints" />
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Report a problem</CardTitle>
        </CardHeader>
        <CardContent>
          <ComplaintForm />
        </CardContent>
      </Card>
      <section aria-labelledby="your-complaints" className="space-y-3">
        <h2 id="your-complaints" className="text-xl font-semibold">
          Your complaints
        </h2>
        {list}
      </section>
    </div>
  );
}
