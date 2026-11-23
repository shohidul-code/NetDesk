import { Pencil, Plus } from "lucide-react";
import { useState } from "react";
import { PageHeader } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { FilterSelect } from "@/features/connections/FilterSelect";
import { useAreas } from "@/features/connections/reference";
import { type Column, ListBoundary, ResponsiveList } from "@/features/connections/ResponsiveList";
import { type Notice, useNotices } from "@/features/notices/api";
import { noticeState } from "@/features/notices/dhaka";
import { EndNoticeDialog } from "@/features/notices/EndNoticeDialog";
import { NoticeSheet } from "@/features/notices/NoticeForm";
import { formatDateTime } from "@/lib/format";

const ACTIVE_OPTIONS = [
  { value: "true", label: "Active now" },
  { value: "false", label: "Not active" },
];

export function NoticesPage() {
  const [filters, setFilters] = useState({ area: "", active: "" });
  const [editing, setEditing] = useState<Notice | null | "new">(null);
  const [ending, setEnding] = useState<Notice | null>(null);
  const areas = useAreas();
  const query = useNotices({
    area_id: filters.area ? Number(filters.area) : undefined,
    active: filters.active ? filters.active === "true" : undefined,
  });
  const now = query.dataUpdatedAt; // when the list was fetched; keeps render pure
  const areaName = (id: number) => areas.data?.find((a) => a.id === id)?.name ?? "—";

  const columns: Column<Notice>[] = [
    { header: "Area", primary: true, cell: (n) => areaName(n.area_id) },
    { header: "State", primary: true, cell: (n) => <StatusBadge status={noticeState(n.starts_at, n.ends_at, now)} /> },
    { header: "Kind", cell: (n) => <StatusBadge status={n.kind} /> },
    {
      header: "Message",
      cell: (n) => (
        <div className="max-w-sm space-y-1 text-left">
          <p lang="bn">{n.message_bn}</p>
          <p className="text-text-muted">{n.message_en}</p>
        </div>
      ),
    },
    { header: "Starts", cell: (n) => <span className="tabular">{formatDateTime(n.starts_at)}</span> },
    { header: "Ends", cell: (n) => <span className="tabular">{formatDateTime(n.ends_at)}</span> },
    {
      header: "Actions",
      actions: true,
      cell: (n) => (
        <>
          <Button variant="outline" className="h-11" onClick={() => setEditing(n)} aria-label={`Edit notice for ${areaName(n.area_id)}`}>
            <Pencil aria-hidden /> Edit
          </Button>
          {noticeState(n.starts_at, n.ends_at, now) !== "ended" && (
            <Button variant="outline" className="h-11 text-danger" onClick={() => setEnding(n)} aria-label={`End notice for ${areaName(n.area_id)}`}>
              End
            </Button>
          )}
        </>
      ),
    },
  ];

  const filtered = Boolean(filters.area || filters.active);
  return (
    <div>
      <PageHeader
        title="Notices"
        actions={
          <Button className="h-11" onClick={() => setEditing("new")}>
            <Plus aria-hidden /> Post a notice
          </Button>
        }
      />
      <div className="mb-4 grid gap-3 sm:max-w-xl sm:grid-cols-2">
        <FilterSelect id="n-area" label="Area" allLabel="All areas" value={filters.area} onChange={(area) => setFilters((f) => ({ ...f, area }))} options={(areas.data ?? []).map((a) => ({ value: String(a.id), label: a.name }))} />
        <FilterSelect id="n-active" label="State" allLabel="All notices" value={filters.active} onChange={(active) => setFilters((f) => ({ ...f, active }))} options={ACTIVE_OPTIONS} />
      </div>
      <ListBoundary query={query} isEmpty={query.data?.length === 0} emptyTitle={filtered ? "No notices match" : "No notices yet"} emptyHint={filtered ? null : <p className="text-sm text-text-muted">Post one to tell an area about an outage or maintenance.</p>}>
        {query.data && <ResponsiveList caption="Notices" rows={query.data} rowKey={(n) => n.id} columns={columns} />}
      </ListBoundary>
      <NoticeSheet
        key={editing === "new" || editing === null ? "new" : editing.id}
        open={editing !== null}
        onOpenChange={(open) => !open && setEditing(null)}
        notice={editing === "new" || editing === null ? null : editing}
        areas={areas.data ?? []}
      />
      <EndNoticeDialog notice={ending} areaName={ending ? areaName(ending.area_id) : ""} onClose={() => setEnding(null)} />
    </div>
  );
}
