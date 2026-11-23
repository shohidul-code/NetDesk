import { categoryLabel } from "@/features/my-complaints/labels";
import { useState } from "react";
import { PageHeader } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/features/connections/FilterSelect";
import { Pagination } from "@/features/connections/Pagination";
import { useAreas, useConnectionLookup } from "@/features/connections/reference";
import { type Column, ListBoundary, ResponsiveList } from "@/features/connections/ResponsiveList";
import { COMPLAINT_STATUSES, type Complaint, type ComplaintStatus, statusLabel, useComplaints } from "@/features/queue/api";
import { ComplaintDialog } from "@/features/queue/ComplaintDialog";
import { hoursOpen } from "@/features/queue/hours";

const PAGE_SIZE = 20;
const STATUS_OPTIONS = COMPLAINT_STATUSES.map((s) => ({ value: s, label: statusLabel(s) }));

export function TechnicianQueuePage() {
  const [filters, setFilters] = useState({ area: "", status: "open", offset: 0 });
  const [selected, setSelected] = useState<Complaint | null>(null);
  const areas = useAreas();
  const lookup = useConnectionLookup();
  const query = useComplaints({
    area_id: filters.area ? Number(filters.area) : undefined,
    status: (filters.status || undefined) as ComplaintStatus | undefined,
    limit: PAGE_SIZE,
    offset: filters.offset,
  });
  const now = query.dataUpdatedAt; // hours are counted as of the last fetch; keeps render pure

  // Complaint rows carry only connection_id; the customer code and area come from the lookup.
  const customer = (c: Complaint) => lookup.data?.get(c.connection_id);
  const areaOf = (c: Complaint) => areas.data?.find((a) => a.id === customer(c)?.area_id)?.name ?? "—";
  const heading = (c: Complaint) => `${customer(c)?.customer_code ?? "Complaint"} · ${areaOf(c)}`;

  const columns: Column<Complaint>[] = [
    { header: "Customer", primary: true, cell: (c) => <span className="tabular">{customer(c)?.customer_code ?? "—"}</span> },
    { header: "Status", primary: true, cell: (c) => <StatusBadge status={c.status} /> },
    { header: "Area", cell: areaOf },
    { header: "Category", cell: (c) => categoryLabel(c.category) },
    { header: "Hours open", numeric: true, cell: (c) => hoursOpen(c.created_at, c.status, c.updated_at, now) },
    {
      header: "Actions",
      actions: true,
      cell: (c) => (
        <Button variant="outline" className="h-11" onClick={() => setSelected(c)} aria-label={`Open complaint from ${customer(c)?.customer_code ?? "customer"}`}>
          Open
        </Button>
      ),
    },
  ];

  const page = query.data;
  return (
    <div>
      <PageHeader title="Complaints" />
      <div className="mb-4 grid gap-3 sm:max-w-xl sm:grid-cols-2">
        <FilterSelect id="q-area" label="Area" allLabel="All areas" value={filters.area} onChange={(area) => setFilters((f) => ({ ...f, area, offset: 0 }))} options={(areas.data ?? []).map((a) => ({ value: String(a.id), label: a.name }))} />
        <FilterSelect id="q-status" label="Status" allLabel="All statuses" value={filters.status} onChange={(status) => setFilters((f) => ({ ...f, status, offset: 0 }))} options={STATUS_OPTIONS} />
      </div>
      <ListBoundary query={query} isEmpty={page?.items.length === 0} emptyTitle={filters.status === "open" ? "No open complaints" : "No complaints match"}>
        {page && (
          <>
            <ResponsiveList caption="Complaints" rows={page.items} rowKey={(c) => c.id} columns={columns} />
            <Pagination total={page.total} limit={PAGE_SIZE} offset={page.offset} onChange={(offset) => setFilters((f) => ({ ...f, offset }))} />
          </>
        )}
      </ListBoundary>
      <ComplaintDialog complaint={selected} heading={selected ? heading(selected) : ""} onClose={() => setSelected(null)} />
    </div>
  );
}
