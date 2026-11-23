import { Loader2 } from "lucide-react";
import { toast } from "sonner";
import { ApiError } from "@/api/errors";
import { FormError } from "@/components/states";
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
import { type Connection, useDeleteConnection } from "./api";

interface Props {
  connection: Connection | null;
  onClose: () => void;
}

export function DeleteConnectionDialog({ connection, onClose }: Props) {
  const remove = useDeleteConnection();
  const hasBills = remove.error instanceof ApiError && remove.error.status === 409;

  async function confirm() {
    if (!connection) return;
    try {
      await remove.mutateAsync(connection.id);
      toast.success(`${connection.customer_code} deleted.`);
      onClose();
    } catch {
      // The error stays in the dialog (409: the customer has bills).
    }
  }

  return (
    <AlertDialog
      open={connection !== null}
      onOpenChange={(open) => {
        if (!open) {
          remove.reset();
          onClose();
        }
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete {connection?.customer_code}?</AlertDialogTitle>
          <AlertDialogDescription>
            This removes {connection?.customer_name} from the network. It cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        {hasBills && (
          <p role="alert" className="text-sm text-danger">
            Has bills — set Disconnected instead.
          </p>
        )}
        {remove.isError && !hasBills && <FormError error={remove.error} />}
        <AlertDialogFooter>
          <AlertDialogCancel className="h-11">Cancel</AlertDialogCancel>
          <Button variant="destructive" className="h-11" disabled={remove.isPending || hasBills} onClick={() => void confirm()}>
            {remove.isPending && <Loader2 className="animate-spin" aria-hidden />}
            Delete connection
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
