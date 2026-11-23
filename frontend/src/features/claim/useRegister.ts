import { useMutation } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

/** POST /auth/register: claims the connection the operator already created. */
export function useRegister() {
  return useMutation({
    mutationFn: (body: Schemas["RegisterRequest"]) => api.post<Schemas["UserRead"]>("/auth/register", body),
  });
}
