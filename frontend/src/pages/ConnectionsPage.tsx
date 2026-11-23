import { Pencil, Plus, Search, Trash2 } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/auth/useAuth";
import { PageHeader } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { type Connection, type ConnectionStatus, useConnections } from "@/features/connections/api";
import { ConnectionSheet } from "@/features/connections/ConnectionForm";
import { DeleteConnectionDialog } from "@/features/connections/DeleteConnectionDialog";
import { FilterSelect } from "@/features/connections/FilterSelect";
import { Pagination } from "@/features/connections/Pagination";
import { useAreas, usePackages } from "@/features/connections/reference";
import { type Column, ListBoundary, ResponsiveList } from "@/features/connections/ResponsiveList";
import { useDebouncedValue } from "@/features/connections/useDebouncedValue";

const PAGE_SIZE = 20;
const STATUSES = ["active", "suspended", "disconnected"].map((s) => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) }));
const SORTS = [
  { value: "-created_at", label: "Newest first" },
  { value: "customer_code", label: "Code, low to high" },
  { value: "customer_name", label: "Name, A to Z" },
];

interface Filters {
  area: string;
  status: string;
  pkg: string;
  sort: string;
  search: string;
  offset: number;
}

export function ConnectionsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin"; // technicians read only; the API enforces it too
  const [filters, setFilters] = useState<Filters>({ area: "", status: "", pkg: "", sort: "", search: "", offset: 0 });
  const [editing, setEditing] = useState<Connection | null | "new">(null);
  const [deleting, setDeleting] = useState<Connection | null>(null);
  const areas = useAreas();
  const packages = usePackages();
  const q = useDebouncedValue(filters.search.trim(), 300);

  const query = useConnections({
    area_id: filters.area ? Number(filters.area) : undefined,
    status: (filters.status || undefined) as ConnectionStatus | undefined,
    package_id: filters.pkg ? Number(filters.pkg) : undefined,
    q: q || undefined,
    sort: filters.sort || undefined,
    limit: PAGE_SIZE,
    offset: filters.offset,
  });
  const change = (patch: Partial<Filters>) => setFilters((f) => ({ ...f, offset: 0, ...patch }));

  const areaName = (id: number) => areas.data?.find((a) => a.id === id)?.name ?? "—";
  const packageName = (id: number) => packages.data?.find((p) => p.id === id)?.name ?? "—";

  const columns: Column<Connection>[] = [
    { header: "Code", primary: true, cell: (c) => <span className="tabular">{c.customer_code}</span> },
    { header: "Status", primary: true, cell: (c) => <StatusBadge status={c.status} /> },
    { header: "Customer", cell: (c) => c.customer_name },
    { header: "Phone", cell: (c) => <span className="tabular">{c.phone}</span> },
    { header: "Package", cell: (c) => packageName(c.package_id) },
    { header: "Area", cell: (c) => areaName(c.area_id) },
  ];
  if (isAdmin) {
    columns.push({
      header: "Actions",
      actions: true,
      cell: (c) => (
        <>
          <Button variant="outline" className="h-11" onClick={() => setEditing(c)} aria-label={`Edit ${c.customer_code}`}>
            <Pencil aria-hidden /> Edit
          </Button>
          <Button variant="outline" className="h-11 text-danger" onClick={() => setDeleting(c)} aria-label={`Delete ${c.customer_code}`}>
            <Trash2 aria-hidden /> Delete
          </Button>
        </>
      ),
    });
  }

  const page = query.data;
  const filtered = Boolean(filters.area || filters.status || filters.pkg || q);
  return (
    <div>
      <PageHeader
        title="Connections"
        actions={
          isAdmin && (
            <Button className="h-11" onClick={() => setEditing("new")}>
              <Plus aria-hidden /> New connection
            </Button>
          )
        }
      />
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <div className="space-y-1.5">
          <Label htmlFor="search">Search</Label>
          <div className="relative">
            <Search className="pointer-events-none absolute top-3.5 left-3 size-4 text-text-muted" aria-hidden />
            <Input id="search" type="search" className="h-11 pl-9" placeholder="Name, code or phone" value={filters.search} onChange={(e) => change({ search: e.target.value })} />
          </div>
        </div>
        <FilterSelect id="f-area" label="Area" allLabel="All areas" value={filters.area} onChange={(area) => change({ area })} options={(areas.data ?? []).map((a) => ({ value: String(a.id), label: a.name }))} />
        <FilterSelect id="f-status" label="Status" allLabel="All statuses" value={filters.status} onChange={(status) => change({ status })} options={STATUSES} />
        <FilterSelect id="f-package" label="Package" allLabel="All packages" value={filters.pkg} onChange={(pkg) => change({ pkg })} options={(packages.data ?? []).map((p) => ({ value: String(p.id), label: p.name }))} />
        <FilterSelect id="f-sort" label="Sort" allLabel="Default order" value={filters.sort} onChange={(sort) => change({ sort })} options={SORTS} />
      </div>

      <ListBoundary query={query} isEmpty={page?.items.length === 0} emptyTitle={filtered ? "No connections match" : "No connections yet"} emptyHint={filtered ? <p className="text-sm text-text-muted">Try clearing a filter or the search.</p> : null}>
        {page && (
          <>
            <ResponsiveList caption="Connections" rows={page.items} rowKey={(c) => c.id} columns={columns} />
            <Pagination total={page.total} limit={PAGE_SIZE} offset={page.offset} onChange={(offset) => setFilters((f) => ({ ...f, offset }))} />
          </>
        )}
      </ListBoundary>

      {isAdmin && (
        <>
          <ConnectionSheet
            key={editing === "new" || editing === null ? "new" : editing.id}
            open={editing !== null}
            onOpenChange={(open) => !open && setEditing(null)}
            connection={editing === "new" || editing === null ? null : editing}
            areas={areas.data ?? []}
            packages={packages.data ?? []}
          />
          <DeleteConnectionDialog connection={deleting} onClose={() => setDeleting(null)} />
        </>
      )}
    </div>
  );
}
