import { ErrorState, LoadingBlock } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useAreas, useMyConnection, usePackages } from "./queries";

export function ConnectionCard() {
  const connection = useMyConnection();
  const packages = usePackages();
  const areas = useAreas();

  let body;
  if (connection.isPending) body = <LoadingBlock lines={2} />;
  else if (connection.isError) body = <ErrorState error={connection.error} onRetry={() => void connection.refetch()} />;
  else if (!connection.data) body = <p className="text-text-muted">No connection is linked to your account. Call your operator.</p>;
  else {
    const c = connection.data;
    const pkg = packages.data?.find((p) => p.id === c.package_id);
    const area = areas.data?.find((a) => a.id === c.area_id);
    body = (
      <div className="space-y-2">
        <div className="flex items-center justify-between gap-2">
          <p className="text-lg font-medium">{pkg ? `${pkg.name} · ${pkg.speed_mbps} Mbps` : "Your package"}</p>
          <StatusBadge status={c.status} />
        </div>
        <p className="text-sm text-text-muted">
          {area ? `${area.name} (${area.name_bn})` : "Your area"} · Customer code {c.customer_code}
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Your connection</CardTitle>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
