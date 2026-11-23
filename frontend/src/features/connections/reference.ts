/** Lookups several pages share: areas, packages, and connections by id (complaints and bills only carry connection_id). */
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";
import type { Connection } from "./api";

export type Area = Schemas["AreaRead"];
export type Package = Schemas["PackageRead"];

export function useAreas() {
  return useQuery({
    queryKey: ["areas"],
    queryFn: () => api.get<Area[]>("/areas"),
    staleTime: 5 * 60_000,
  });
}

export function usePackages() {
  return useQuery({
    queryKey: ["packages"],
    queryFn: () => api.get<Package[]>("/packages"),
    staleTime: 5 * 60_000,
  });
}

const PAGE = 100; // the API's maximum page size

/**
 * Every connection the user may see, keyed by id. The API's complaint and bill rows hold only
 * connection_id, so the queue and the bill list look the customer code and area up here.
 * shortcut: loads all pages up front; fine for a small ISP, replace with a per-row fetch past a few thousand.
 */
export function useConnectionLookup() {
  return useQuery({
    queryKey: ["connections", "lookup"],
    staleTime: 60_000,
    queryFn: async () => {
      const byId = new Map<string, Connection>();
      let offset = 0;
      for (;;) {
        const page = await api.get<Schemas["Page_ConnectionRead_"]>("/connections", { limit: PAGE, offset });
        page.items.forEach((c) => byId.set(c.id, c));
        offset += PAGE;
        if (offset >= page.total || page.items.length === 0) return byId;
      }
    },
  });
}
