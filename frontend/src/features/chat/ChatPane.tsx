import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { ApiError } from "@/api/errors";
import { ErrorState, LoadingBlock } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Composer } from "./Composer";
import { MessageBubble } from "./MessageBubble";
import { addPendingMessage, addReply, removeMessage, toItem } from "./messages";
import { sessionsKey, useCreateSession, useMessages, useSendMessage } from "./queries";

const SUGGESTIONS = ["How much do I owe?", "My internet is down", "How do I pay by bKash?"];

interface Props {
  sessionId: string | null;
  onSession: (id: string) => void;
  onLeft: (n: number) => void;
  /** True when today's messages are used up. */
  outOfMessages: boolean;
  onOutOfMessages: () => void;
}

interface Failure {
  content: string;
  message: string;
  canRetry: boolean;
}

/** 429 with code quota_exceeded is the daily limit; any other 429 is the per-minute limit. */
function describe(error: unknown, content: string): Failure {
  if (error instanceof ApiError && error.status === 429 && error.code === "quota_exceeded")
    return { content, message: "You have used today's messages. Try again tomorrow.", canRetry: false };
  if (error instanceof ApiError && error.status === 429)
    return { content, message: "You are sending messages too fast. Wait a minute and try again.", canRetry: true };
  if (error instanceof ApiError && error.status === 503)
    return { content, message: "The assistant is temporarily offline.", canRetry: true };
  return { content, message: "Something went wrong. Please try again.", canRetry: true };
}

export function ChatPane({ sessionId, onSession, onLeft, outOfMessages, onOutOfMessages }: Props) {
  const queryClient = useQueryClient();
  const messages = useMessages(sessionId);
  const createSession = useCreateSession();
  const sendMessage = useSendMessage();
  const [text, setText] = useState("");
  const [failure, setFailure] = useState<Failure | null>(null);
  const bottom = useRef<HTMLDivElement>(null);
  const itemCount = messages.data?.length ?? 0;

  useEffect(() => {
    bottom.current?.scrollIntoView?.({ block: "end" });
  }, [itemCount, sendMessage.isPending, failure]);

  async function send(content: string) {
    setFailure(null);
    setText("");
    let chatId = sessionId;
    let pendingId: string | null = null;
    try {
      chatId ??= (await createSession.mutateAsync()).id;
      pendingId = await addPendingMessage(queryClient, chatId, content);
      if (chatId !== sessionId) onSession(chatId);
      const reply = await sendMessage.mutateAsync({ chatId, content });
      addReply(queryClient, chatId, reply);
      onLeft(reply.messages_left_today);
      void queryClient.invalidateQueries({ queryKey: sessionsKey }); // the title is set by the first message
    } catch (error) {
      if (chatId && pendingId) removeMessage(queryClient, chatId, pendingId);
      setText(content); // keep what the user typed
      setFailure(describe(error, content));
      if (error instanceof ApiError && error.code === "quota_exceeded") onOutOfMessages();
    }
  }

  const items = (messages.data ?? []).map(toItem);
  let body;
  if (messages.isPending && sessionId !== null) body = <LoadingBlock />;
  else if (messages.isError) body = <ErrorState error={messages.error} onRetry={() => void messages.refetch()} />;
  else if (items.length === 0 && !sendMessage.isPending)
    body = (
      <div className="m-auto max-w-sm space-y-4 text-center">
        <p className="text-lg font-medium">Hello! Ask me about your bill, your connection or an outage.</p>
        <div className="flex flex-wrap justify-center gap-2">
          {SUGGESTIONS.map((s) => (
            <Button key={s} variant="outline" className="h-auto min-h-11 whitespace-normal" disabled={outOfMessages} onClick={() => void send(s)}>
              {s}
            </Button>
          ))}
        </div>
      </div>
    );
  else body = items.map((item) => <MessageBubble key={item.id} item={item} />);

  return (
    <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-border bg-bg">
      <div role="log" aria-live="polite" aria-label="Conversation" className="flex flex-1 flex-col gap-3 overflow-y-auto p-4">
        {body}
        {sendMessage.isPending && <p className="text-sm text-text-muted">Thinking…</p>}
        {failure && (
          <div role="alert" className="flex flex-wrap items-center gap-3 text-sm text-danger">
            <span>{failure.message}</span>
            {failure.canRetry && (
              <Button size="sm" variant="outline" onClick={() => void send(failure.content)}>
                Retry
              </Button>
            )}
          </div>
        )}
        <div ref={bottom} />
      </div>
      <Composer text={text} onText={setText} onSend={(c) => void send(c)} pending={sendMessage.isPending || createSession.isPending} disabled={outOfMessages} />
    </div>
  );
}
