import { SearchX } from "lucide-react";
import { cn } from "@/lib/utils";
import { toolLabel, type ChatItem } from "./messages";

export function MessageBubble({ item }: { item: ChatItem }) {
  const isUser = item.role === "user";
  return (
    <div className={cn("flex flex-col gap-1.5", isUser ? "items-end" : "items-start")}>
      <div
        className={cn(
          "max-w-[85%] whitespace-pre-wrap break-words rounded-2xl px-4 py-2.5",
          isUser && "bg-primary text-white",
          !isUser && !item.noInformation && "border border-border bg-surface",
          item.noInformation && "border border-dashed border-warning bg-warning/10",
        )}
      >
        {item.noInformation && (
          <p className="mb-1 flex items-center gap-1.5 text-sm font-medium text-warning">
            <SearchX className="size-4" aria-hidden />
            No information found
          </p>
        )}
        {item.content}
      </div>
      {(item.tools.length > 0 || item.sources.length > 0) && (
        <ul className="flex max-w-[85%] flex-wrap gap-1.5" aria-label="How this answer was made">
          {item.tools.map((t, i) => (
            <li key={`${t.name}-${i}`} className="rounded-full border border-border bg-bg px-2.5 py-0.5 text-xs">
              {toolLabel(t.name)}
              {!t.ok && <span className="text-danger"> (failed)</span>}
            </li>
          ))}
          {item.sources.map((s) => (
            <li key={s.ref} className="rounded-full border border-primary/30 bg-primary/10 px-2.5 py-0.5 text-xs text-primary">
              {s.ref}
              {s.title && ` · ${s.title}`}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
