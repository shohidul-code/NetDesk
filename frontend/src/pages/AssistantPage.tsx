import { History } from "lucide-react";
import { useState } from "react";
import { useAuth } from "@/auth/useAuth";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { ChatPane } from "@/features/chat/ChatPane";
import { SessionList } from "@/features/chat/SessionList";
import { cn } from "@/lib/utils";

export function AssistantPage() {
  const { user } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const [outOfMessages, setOutOfMessages] = useState(false);
  const [listOpen, setListOpen] = useState(false);

  function select(id: string | null) {
    setSessionId(id);
    setListOpen(false);
  }

  const exhausted = outOfMessages || left === 0;
  // Height left under the app header (and the customer bottom bar on phones).
  const height =
    user?.role === "customer"
      ? "h-[calc(100dvh-10.5rem)] sm:h-[calc(100dvh-6.5rem)]"
      : "h-[calc(100dvh-5.5rem)] sm:h-[calc(100dvh-6.5rem)]";

  return (
    <div className={cn("flex flex-col gap-3", height)}>
      <div className="flex items-center justify-between gap-3">
        <h1 className="text-2xl font-semibold">Assistant</h1>
        <div className="flex items-center gap-3">
          {left !== null && (
            <p className="text-sm text-text-muted">
              {left} {left === 1 ? "message" : "messages"} left today
            </p>
          )}
          <Sheet open={listOpen} onOpenChange={setListOpen}>
            <SheetTrigger asChild>
              <Button variant="outline" className="h-11 sm:hidden">
                <History aria-hidden />
                Chats
              </Button>
            </SheetTrigger>
            <SheetContent side="left" className="w-80 overflow-y-auto p-4">
              <SheetHeader className="p-0 pb-3">
                <SheetTitle>Your chats</SheetTitle>
              </SheetHeader>
              <SessionList selectedId={sessionId} onSelect={select} />
            </SheetContent>
          </Sheet>
        </div>
      </div>
      <div className="flex min-h-0 flex-1 gap-4">
        <aside className="hidden w-64 shrink-0 overflow-y-auto sm:block" aria-label="Your chats">
          <SessionList selectedId={sessionId} onSelect={select} />
        </aside>
        <ChatPane
          sessionId={sessionId}
          onSession={setSessionId}
          onLeft={(n) => {
            setLeft(n);
            if (n <= 0) setOutOfMessages(true);
          }}
          outOfMessages={exhausted}
          onOutOfMessages={() => setOutOfMessages(true)}
        />
      </div>
    </div>
  );
}
