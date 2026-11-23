import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

export type Notice = Schemas["NoticeRead"];
export type NoticeKind = Schemas["NoticeCreate"]["kind"];
/** The body both POST and PATCH accept; the form always sends every field. */
export type NoticeBody = Schemas["NoticeCreate"];

export type NoticeFilters = { area_id?: number; active?: boolean };

/** The API returns a plain array here: notices are not paginated. */
export function useNotices(filters: NoticeFilters) {
  return useQuery({
    queryKey: ["notices", filters],
    queryFn: () => api.get<Notice[]>("/notices", filters),
  });
}

type SaveInput = { id: null; body: NoticeBody } | { id: string; body: Schemas["NoticeUpdate"] };

export function useSaveNotice() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveInput) =>
      input.id === null ? api.post<Notice>("/notices", input.body) : api.patch<Notice>(`/notices/${input.id}`, input.body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notices"] }),
  });
}
