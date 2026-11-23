/** Loading, empty and error states every list and card uses (UI.md §7). */
import { AlertTriangle, Inbox } from "lucide-react";
import type { ReactNode } from "react";
import { ApiError } from "@/api/errors";
import { friendlyMessage } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

export function LoadingBlock({ lines = 3 }: { lines?: number }) {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="Loading">
      {Array.from({ length: lines }, (_, i) => (
        <Skeleton key={i} className="h-12 w-full" />
      ))}
    </div>
  );
}

export function EmptyState({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-border bg-surface p-8 text-center">
      <Inbox className="size-8 text-text-muted" aria-hidden />
      <p className="font-medium">{title}</p>
      {children}
    </div>
  );
}

/** Friendly text, Retry, and the request_id under "Details" so users can quote it. */
export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = error instanceof ApiError ? error : null;
  const message = apiError ? friendlyMessage(apiError) : "Something went wrong. Please try again.";
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-lg border border-danger/30 bg-surface p-4">
      <p className="flex items-center gap-2 text-danger">
        <AlertTriangle className="size-5 shrink-0" aria-hidden />
        {message}
      </p>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          Try again
        </Button>
      )}
      {apiError?.requestId && (
        <details className="text-sm text-text-muted">
          <summary className="cursor-pointer">Details</summary>
          Reference: <code>{apiError.requestId}</code>
        </details>
      )}
    </div>
  );
}

/** A form-level error under a form: 409 shows the server's own sentence (UI.md §8). */
export function FormError({ error }: { error: unknown }) {
  if (!error) return null;
  const apiError = error instanceof ApiError ? error : null;
  return (
    <p role="alert" className="text-sm text-danger">
      {apiError ? friendlyMessage(apiError) : "Something went wrong. Please try again."}
      {apiError?.requestId && <span className="block text-xs text-text-muted">Reference: {apiError.requestId}</span>}
    </p>
  );
}

export function PageHeader({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
      <h1 className="text-2xl font-semibold">{title}</h1>
      {actions}
    </div>
  );
}
