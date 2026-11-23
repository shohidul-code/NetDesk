import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

/** A customer's list endpoints only ever return their own rows (the API scopes them). */
export function useMyConnection() {
  return useQuery({
    queryKey: ["connections", "mine"],
    queryFn: async () => (await api.get<Schemas["Page_ConnectionRead_"]>("/connections", { limit: 1 })).items[0] ?? null,
  });
}

export function usePackages() {
  return useQuery({ queryKey: ["packages"], queryFn: () => api.get<Schemas["PackageRead"][]>("/packages") });
}

export function useAreas() {
  return useQuery({ queryKey: ["areas"], queryFn: () => api.get<Schemas["AreaRead"][]>("/areas") });
}

/** 100 is the API's maximum page size; a customer has far fewer bills than that. */
export function useBills() {
  return useQuery({
    queryKey: ["bills", "mine"],
    queryFn: async () => {
      const { items } = await api.get<Schemas["Page_BillRead_"]>("/bills", { limit: 100 });
      return [...items].sort((a, b) => b.period.localeCompare(a.period));
    },
  });
}

export function useActiveNotices() {
  return useQuery({
    queryKey: ["notices", "active"],
    queryFn: () => api.get<Schemas["NoticeRead"][]>("/notices", { active: true }),
  });
}
