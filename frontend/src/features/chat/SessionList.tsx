import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import type { Schemas } from "@/api/types";
import { EmptyState, ErrorState, LoadingBlock } from "@/components/states";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import { useCreateSession, useDeleteSession, useSessions } from "./queries";

interface Props {
  selectedId: string | null;
  onSelect: (id: string | null) => void;
}

export function SessionList({ selectedId, onSelect }: Props) {
  const sessions = useSessions();
  const create = useCreateSession();
  const remove = useDeleteSession();
  const [toDelete, setToDelete] = useState<Schemas["SessionRead"] | null>(null);

  async function newChat() {
    try {
      onSelect((await create.mutateAsync()).id);
    } catch {
      toast.error("Could not start a new chat. Please try again.");
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    try {
      await remove.mutateAsync(toDelete.id);
      if (toDelete.id === selectedId) onSelect(null);
      toast.success("Chat deleted.");
    } catch {
      toast.error("Could not delete this chat. Please try again.");
    }
    setToDelete(null);
  }

  let list;
  if (sessions.isPending) list = <LoadingBlock lines={4} />;
  else if (sessions.isError) list = <ErrorState error={sessions.error} onRetry={() => void sessions.refetch()} />;
  else if (sessions.data.length === 0) list = <EmptyState title="No chats yet" />;
  else
    list = (
      <ul className="space-y-1">
        {sessions.data.map((s) => (
          <li key={s.id} className="flex items-center gap-1">
            <button
              type="button"
              onClick={() => onSelect(s.id)}
              aria-current={s.id === selectedId ? "true" : undefined}
              className={cn(
                "min-h-11 min-w-0 flex-1 rounded-md px-3 py-1.5 text-left hover:bg-bg",
                s.id === selectedId && "bg-primary/10",
              )}
            >
              <span className="block truncate text-sm font-medium">{s.title}</span>
              <span className="block text-xs text-text-muted">{formatDateTime(s.updated_at)}</span>
            </button>
            <Button variant="ghost" size="icon" className="size-11 shrink-0" aria-label={`Delete chat ${s.title}`} onClick={() => setToDelete(s)}>
              <Trash2 aria-hidden />
            </Button>
          </li>
        ))}
      </ul>
    );

  return (
    <div className="space-y-3">
      <Button className="h-11 w-full" onClick={() => void newChat()} disabled={create.isPending}>
        <Plus aria-hidden />
        New chat
      </Button>
      {list}
      <AlertDialog open={toDelete !== null} onOpenChange={(open) => !open && setToDelete(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this chat?</AlertDialogTitle>
            <AlertDialogDescription>
              "{toDelete?.title}" and its messages will be removed from your list.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep chat</AlertDialogCancel>
            <AlertDialogAction
              disabled={remove.isPending}
              onClick={(e) => {
                e.preventDefault();
                void confirmDelete();
              }}
            >
              Delete chat
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
