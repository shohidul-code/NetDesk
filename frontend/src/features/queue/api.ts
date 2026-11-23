import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

export type Complaint = Schemas["ComplaintRead"];
export type ComplaintStatus = NonNullable<Schemas["ComplaintUpdate"]["status"]>;
export const COMPLAINT_STATUSES: ComplaintStatus[] = ["open", "in_progress", "resolved", "closed"];

export const statusLabel = (s: string) => (s === "in_progress" ? "In progress" : s.charAt(0).toUpperCase() + s.slice(1));

export type ComplaintFilters = { status?: ComplaintStatus; area_id?: number; limit: number; offset: number };

export function useComplaints(filters: ComplaintFilters) {
  return useQuery({
    queryKey: ["complaints", "queue", filters],
    queryFn: () => api.get<Schemas["Page_ComplaintRead_"]>("/complaints", filters),
    placeholderData: keepPreviousData,
  });
}

/** Staff change the status only: assigned_to is admin-only in the API and needs a technician id. */
export function useUpdateComplaint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ComplaintStatus }) =>
      api.patch<Complaint>(`/complaints/${id}`, { status } satisfies Schemas["ComplaintUpdate"]),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["complaints"] }),
  });
}
