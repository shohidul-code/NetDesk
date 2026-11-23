import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

export type Bill = Schemas["BillRead"];
export type BillStatus = Bill["status"];
export type PaymentMethod = Schemas["PaymentCreate"]["payment_method"];

export const PAYMENT_METHODS: { value: PaymentMethod; label: string }[] = [
  { value: "bkash", label: "bKash" },
  { value: "nagad", label: "Nagad" },
  { value: "cash", label: "Cash" },
  { value: "bank", label: "Bank" },
];

export type BillFilters = { status?: BillStatus; period?: string; limit: number; offset: number };

export function useBills(filters: BillFilters) {
  return useQuery({
    queryKey: ["bills", "list", filters],
    queryFn: () => api.get<Schemas["Page_BillRead_"]>("/bills", filters),
    placeholderData: keepPreviousData,
  });
}

export function useGenerateBills() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (period: string) =>
      api.post<Schemas["GenerateResult"]>("/bills/generate", { period } satisfies Schemas["GenerateBills"]),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bills"] }),
  });
}

export function useRecordPayment() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ billId, body }: { billId: string; body: Schemas["PaymentCreate"] }) =>
      api.post<Bill>(`/bills/${billId}/payment`, body),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["bills"] }),
  });
}
