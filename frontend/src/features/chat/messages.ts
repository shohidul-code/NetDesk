import type { QueryClient } from "@tanstack/react-query";
import type { Schemas } from "@/api/types";
import { messagesKey } from "./queries";

type Message = Schemas["MessageRead"];

export interface ToolChip {
  name: string;
  ok: boolean;
}
export interface SourceChip {
  ref: string;
  title: string;
}
export interface ChatItem {
  id: string;
  role: "user" | "assistant";
  content: string;
  tools: ToolChip[];
  sources: SourceChip[];
  noInformation: boolean;
}

const TOOL_LABEL: Record<string, string> = {
  get_my_bill_status: "Checked your bill",
  get_my_area_status: "Checked your area",
  get_area_service_status: "Checked area service status",
};

export function toolLabel(name: string): string {
  return TOOL_LABEL[name] ?? name.replace(/_/g, " ");
}

/** Stored history has loose dicts, so each field is checked before use. */
export function toItem(m: Message): ChatItem {
  const tools = m.tools_used.flatMap((t) =>
    typeof t.name === "string" ? [{ name: t.name, ok: t.ok === true }] : [],
  );
  const sources = m.sources.flatMap((s) =>
    typeof s.ref === "string" ? [{ ref: s.ref, title: typeof s.title === "string" ? s.title : "" }] : [],
  );
  const role = m.role === "user" ? "user" : "assistant";
  // GET messages has no no_information field, so use the server's own rule
  // (app/modules/chat/services.py): no sources and no successful tool.
  const noInformation = role === "assistant" && sources.length === 0 && !tools.some((t) => t.ok);
  return { id: m.id, role, content: m.content, tools, sources, noInformation };
}

function update(queryClient: QueryClient, chatId: string, fn: (old: Message[]) => Message[]) {
  queryClient.setQueryData<Message[]>(messagesKey(chatId), (old) => fn(old ?? []));
}

/** The user's message shows at once, before the server answers. Returns its temporary id. */
export async function addPendingMessage(queryClient: QueryClient, chatId: string, content: string): Promise<string> {
  await queryClient.cancelQueries({ queryKey: messagesKey(chatId) });
  const id = `pending-${Date.now()}`;
  update(queryClient, chatId, (old) => [
    ...old,
    { id, role: "user", content, tools_used: [], sources: [], created_at: new Date().toISOString() },
  ]);
  return id;
}

export function removeMessage(queryClient: QueryClient, chatId: string, id: string) {
  update(queryClient, chatId, (old) => old.filter((m) => m.id !== id));
}

export function addReply(queryClient: QueryClient, chatId: string, reply: Schemas["ChatReply"]) {
  update(queryClient, chatId, (old) => [
    ...old,
    {
      id: reply.message_id,
      role: "assistant",
      content: reply.content,
      tools_used: reply.tools_used,
      sources: reply.sources,
      created_at: new Date().toISOString(),
    },
  ]);
}
