import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Schemas } from "@/api/types";

export const sessionsKey = ["chat", "sessions"] as const;
export const messagesKey = (chatId: string) => ["chat", "messages", chatId] as const;

export function useSessions() {
  return useQuery({ queryKey: sessionsKey, queryFn: () => api.get<Schemas["SessionRead"][]>("/chat/sessions") });
}

/** History lives on the server; opening a session loads it, nothing is resent (RULES §6). */
export function useMessages(chatId: string | null) {
  return useQuery({
    queryKey: messagesKey(chatId ?? ""),
    queryFn: () => api.get<Schemas["MessageRead"][]>(`/chat/sessions/${chatId}/messages`),
    enabled: chatId !== null,
  });
}

export function useCreateSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Schemas["SessionRead"]>("/chat/sessions"),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sessionsKey }),
  });
}

export function useDeleteSession() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (chatId: string) => api.delete(`/chat/sessions/${chatId}`),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: sessionsKey }),
  });
}

/** Sends only the new message; the server already holds the history. */
export function useSendMessage() {
  return useMutation({
    mutationFn: ({ chatId, content }: { chatId: string; content: string }) =>
      api.post<Schemas["ChatReply"]>(`/chat/sessions/${chatId}/messages`, { content }),
  });
}
