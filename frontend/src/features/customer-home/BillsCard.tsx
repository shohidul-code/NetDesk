import { EmptyState, ErrorState, LoadingBlock } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatDate, formatDateTime, formatMoney, formatMonth } from "@/lib/format";
import { useBills } from "./queries";

export function BillsCard() {
  const bills = useBills();

  let body;
  if (bills.isPending) body = <LoadingBlock />;
  else if (bills.isError) body = <ErrorState error={bills.error} onRetry={() => void bills.refetch()} />;
  else if (bills.data.length === 0) body = <EmptyState title="No bills yet" />;
  else {
    const unpaid = bills.data.filter((b) => b.status === "unpaid");
    // Money arrives as a decimal string; the sum of a few bills is exact enough in a Number.
    const totalDue = unpaid.reduce((sum, b) => sum + Number(b.amount_bdt), 0);
    const nextDue = unpaid.map((b) => b.due_date).sort()[0];
    body = (
      <div className="space-y-4">
        <div>
          <p className="text-sm text-text-muted">Total due</p>
          {unpaid.length === 0 ? (
            <p className="text-3xl font-semibold text-success">All paid</p>
          ) : (
            <>
              <p className="text-3xl font-semibold tabular-nums">{formatMoney(totalDue)}</p>
              {nextDue && <p className="text-sm text-text-muted">Next due date: {formatDate(nextDue)}</p>}
            </>
          )}
        </div>
        <ul className="divide-y divide-border">
          {bills.data.map((bill) => (
            <li key={bill.id} className="flex items-center justify-between gap-3 py-3">
              <div>
                <p className="font-medium">{formatMonth(bill.period)}</p>
                {bill.paid_at && <p className="text-sm text-text-muted">Paid {formatDateTime(bill.paid_at)}</p>}
              </div>
              <div className="flex items-center gap-3">
                <span className="tabular-nums">{formatMoney(bill.amount_bdt)}</span>
                <StatusBadge status={bill.status} />
              </div>
            </li>
          ))}
        </ul>
        <p className="text-sm text-text-muted">
          To pay, send the amount by bKash or Nagad to your operator, then give them the TrxID. They mark the bill paid.
        </p>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Your bills</CardTitle>
      </CardHeader>
      <CardContent>{body}</CardContent>
    </Card>
  );
}
