import { Link } from "react-router";
import { ErrorState, LoadingBlock } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { categoryLabel } from "@/features/my-complaints/labels";
import { useComplaints } from "@/features/my-complaints/queries";
import { formatDateTime } from "@/lib/format";

export function LatestComplaint() {
  const complaints = useComplaints();
  const latest = complaints.data?.[0];

  let body;
  if (complaints.isPending) body = <LoadingBlock lines={1} />;
  else if (complaints.isError) body = <ErrorState error={complaints.error} onRetry={() => void complaints.refetch()} />;
  else if (!latest)
    body = (
      <Button asChild variant="outline" className="h-11">
        <Link to="/complaints">Report a problem</Link>
      </Button>
    );
  else
    body = (
      <Link to="/complaints" className="flex items-center justify-between gap-3 rounded-md hover:bg-bg">
        <div>
          <p className="font-medium">{categoryLabel(latest.category)}</p>
          <p className="text-sm text-text-muted">{formatDateTime(latest.created_at)}</p>
        </div>
        <StatusBadge status={latest.status} />
      </Link>
    );

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Latest complaint</CardTitle>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
