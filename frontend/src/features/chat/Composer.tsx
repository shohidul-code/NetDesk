import { Loader2, SendHorizontal } from "lucide-react";
import { useState, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

export const MAX_LENGTH = 1000;

interface Props {
  text: string;
  onText: (text: string) => void;
  onSend: (content: string) => void;
  pending: boolean;
  disabled: boolean;
}

export function Composer({ text, onText, onSend, pending, disabled }: Props) {
  const [composing, setComposing] = useState(false); // Bangla and other IMEs use Enter to pick a word
  const content = text.trim();
  const canSend = content.length > 0 && !pending && !disabled;

  function onKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey && !composing && !e.nativeEvent.isComposing) {
      e.preventDefault();
      if (canSend) onSend(content);
    }
  }

  return (
    <form
      className="flex items-end gap-2 border-t border-border bg-surface p-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (canSend) onSend(content);
      }}
    >
      <Textarea
        aria-label="Message"
        value={text}
        maxLength={MAX_LENGTH}
        rows={1}
        disabled={disabled}
        placeholder="Type your message"
        className="max-h-32 min-h-11 flex-1 resize-none"
        onChange={(e) => onText(e.target.value)}
        onKeyDown={onKeyDown}
        onCompositionStart={() => setComposing(true)}
        onCompositionEnd={() => setComposing(false)}
      />
      <Button type="submit" className="size-11 shrink-0" disabled={!canSend} aria-label="Send message">
        {pending ? <Loader2 className="animate-spin" aria-hidden /> : <SendHorizontal aria-hidden />}
      </Button>
    </form>
  );
}
