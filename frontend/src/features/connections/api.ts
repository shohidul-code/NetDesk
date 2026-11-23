import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

export type Connection = Schemas["ConnectionRead"];
export type ConnectionStatus = Schemas["ConnectionCreate"]["status"];

export type ConnectionFilters = {
  area_id?: number;
  status?: ConnectionStatus;
  package_id?: number;
  q?: string;
  sort?: string;
  limit: number;
  offset: number;
};

export function useConnections(filters: ConnectionFilters) {
  return useQuery({
    queryKey: ["connections", "list", filters],
    queryFn: () => api.get<Schemas["Page_ConnectionRead_"]>("/connections", filters),
    placeholderData: keepPreviousData,
  });
}

type SaveInput =
  | { id: null; body: Schemas["ConnectionCreate"] }
  | { id: string; body: Schemas["ConnectionUpdate"] };

/** Create (POST) or edit (PATCH); refreshes every connection list and the lookups that read them. */
export function useSaveConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (input: SaveInput) =>
      input.id === null
        ? api.post<Connection>("/connections", input.body)
        : api.patch<Connection>(`/connections/${input.id}`, input.body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });
}

export function useDeleteConnection() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete(`/connections/${id}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["connections"] }),
  });
}
