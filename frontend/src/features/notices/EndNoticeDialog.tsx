import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { ServerError } from "@/features/connections/fields";
import { type Notice, useSaveNotice } from "./api";

interface Props {
  notice: Notice | null;
  /** The area's name, so the dialog names what it ends. */
  areaName: string;
  onClose: () => void;
}

/** Ending a notice is a PATCH that sets ends_at to now; the row then shows as Ended. */
export function EndNoticeDialog({ notice, areaName, onClose }: Props) {
  const save = useSaveNotice();

  async function confirm() {
    if (!notice) return;
    try {
      await save.mutateAsync({ id: notice.id, body: { ends_at: new Date().toISOString() } });
      toast.success("Notice ended.");
      onClose();
    } catch {
      // The reason (for example a notice that has not started yet) stays in the dialog.
    }
  }

  return (
    <AlertDialog
      open={notice !== null}
      onOpenChange={(open) => {
        if (!open) {
          save.reset();
          onClose();
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>End the {notice?.kind} notice for {areaName}?</AlertDialogTitle>
          <AlertDialogDescription>{notice?.message_en} Customers in this area stop seeing it right away.</AlertDialogDescription>
        </AlertDialogHeader>
        <ServerError error={save.error} />
        <AlertDialogFooter>
          <AlertDialogCancel className="h-11">Keep it</AlertDialogCancel>
          <Button variant="destructive" className="h-11" disabled={save.isPending} onClick={() => void confirm()}>
            {save.isPending && <Loader2 className="animate-spin" aria-hidden />}
            End notice
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
