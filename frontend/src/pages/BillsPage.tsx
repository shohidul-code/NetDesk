import { Plus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type Bill, type BillStatus, useBills } from "@/features/bills/api";
import { GenerateDialog } from "@/features/bills/GenerateDialog";
import { PaymentDialog } from "@/features/bills/PaymentDialog";
import { FilterSelect } from "@/features/connections/FilterSelect";
import { Pagination } from "@/features/connections/Pagination";
import { useConnectionLookup } from "@/features/connections/reference";
import { type Column, ListBoundary, ResponsiveList } from "@/features/connections/ResponsiveList";
import { formatDate, formatMoney, formatMonth } from "@/lib/format";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = ["unpaid", "paid", "waived"].map((s) => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) }));
const PERIOD = /^\d{4}-(0[1-9]|1[0-2])$/;

export function BillsPage() {
  const [filters, setFilters] = useState({ status: "", period: "", offset: 0 });
  const [generating, setGenerating] = useState(false);
  const [paying, setPaying] = useState<Bill | null>(null);
  const lookup = useConnectionLookup();
  // A half-typed month is not sent: the API would answer 422.
  const period = PERIOD.test(filters.period) ? filters.period : undefined;
  const query = useBills({ status: (filters.status || undefined) as BillStatus | undefined, period, limit: PAGE_SIZE, offset: filters.offset });

  // Bill rows carry only connection_id; the customer code comes from the lookup.
  const code = (b: Bill) => lookup.data?.get(b.connection_id)?.customer_code ?? "—";

  const columns: Column<Bill>[] = [
    { header: "Customer", primary: true, cell: (b) => <span className="tabular">{code(b)}</span> },
    { header: "Status", primary: true, cell: (b) => <StatusBadge status={b.status} /> },
    { header: "Month", cell: (b) => formatMonth(b.period) },
    { header: "Amount", numeric: true, cell: (b) => formatMoney(b.amount_bdt) },
    { header: "Due", cell: (b) => formatDate(b.due_date) },
    {
      header: "Actions",
      actions: true,
      cell: (b) =>
        b.status === "unpaid" && (
          <Button variant="outline" className="h-11" onClick={() => setPaying(b)} aria-label={`Verify payment for ${code(b)}, ${formatMonth(b.period)}`}>
            Verify payment
          </Button>
        ),
    },
  ];

  const page = query.data;
  const filtered = Boolean(filters.status || period);
  return (
    <div>
      <PageHeader
        title="Bills"
        actions={
          <Button className="h-11" onClick={() => setGenerating(true)}>
            <Plus aria-hidden /> Generate bills for a month
          </Button>
        }
      />
      <div className="mb-4 grid gap-3 sm:max-w-xl sm:grid-cols-2">
        <FilterSelect id="b-status" label="Status" allLabel="All statuses" value={filters.status} onChange={(status) => setFilters((f) => ({ ...f, status, offset: 0 }))} options={STATUS_OPTIONS} />
        <div className="space-y-1.5">
          <Label htmlFor="b-period">Month</Label>
          <Input id="b-period" type="month" placeholder="YYYY-MM" className="h-11" value={filters.period} onChange={(e) => setFilters((f) => ({ ...f, period: e.target.value, offset: 0 }))} />
        </div>
      </div>
      <ListBoundary query={query} isEmpty={page?.items.length === 0} emptyTitle={filtered ? "No bills match" : "No bills yet"} emptyHint={filtered ? null : <Button className="h-11" onClick={() => setGenerating(true)}>Generate bills for a month</Button>}>
        {page && (
          <>
            <ResponsiveList caption="Bills" rows={page.items} rowKey={(b) => b.id} columns={columns} />
            <Pagination total={page.total} limit={PAGE_SIZE} offset={page.offset} onChange={(offset) => setFilters((f) => ({ ...f, offset }))} />
          </>
        )}
      </ListBoundary>
      <GenerateDialog open={generating} onOpenChange={setGenerating} />
      <PaymentDialog bill={paying} customer={paying ? code(paying) : ""} onClose={() => setPaying(null)} />
    </div>
  );
}
