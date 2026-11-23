import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

/** Newest first. A customer only gets their own complaints. */
export function useComplaints() {
  return useQuery({
    queryKey: ["complaints", "mine"],
    queryFn: async () => {
      const { items } = await api.get<Schemas["Page_ComplaintRead_"]>("/complaints", { limit: 100 });
      return [...items].sort((a, b) => b.created_at.localeCompare(a.created_at));
    },
  });
}

export function useCreateComplaint() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Schemas["ComplaintCreate"]) => api.post<Schemas["ComplaintRead"]>("/complaints", body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["complaints"] }),
  });
}
