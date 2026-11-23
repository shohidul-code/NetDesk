import { Loader2 } from "lucide-react";
import { useState } from "react";
import { toast } from "sonner";
import { FormError } from "@/components/states";
import { StatusBadge } from "@/components/StatusBadge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { formatDateTime } from "@/lib/format";
import { COMPLAINT_STATUSES, type Complaint, type ComplaintStatus, statusLabel, useUpdateComplaint } from "./api";

interface Props {
  complaint: Complaint | null;
  /** For example "ND-000012 · Mirpur 10". */
  heading: string;
  onClose: () => void;
}

export function ComplaintDialog({ complaint, heading, onClose }: Props) {
  return (
    <Dialog open={complaint !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        {complaint && <Body key={complaint.id} complaint={complaint} heading={heading} onClose={onClose} />}
      </DialogContent>
    </Dialog>
  );
}

function Body({ complaint, heading, onClose }: Props & { complaint: Complaint }) {
  const update = useUpdateComplaint();
  const [status, setStatus] = useState<ComplaintStatus>(complaint.status as ComplaintStatus);

  async function save() {
    try {
      await update.mutateAsync({ id: complaint.id, status });
      toast.success("Status updated.");
      onClose();
    } catch {
      // A 409 (invalid change) stays inline under the select.
    }
  }

  return (
    <>
      <DialogHeader>
        <DialogTitle>{heading}</DialogTitle>
        <DialogDescription>
          {complaint.category} · reported {formatDateTime(complaint.created_at)}
        </DialogDescription>
      </DialogHeader>
      <p className="whitespace-pre-wrap rounded-md bg-bg p-3 text-sm">{complaint.description}</p>
      <p className="flex items-center gap-2 text-sm">
        Now: <StatusBadge status={complaint.status} />
      </p>
      <div className="space-y-1.5">
        <Label htmlFor="complaint-status">Change status to</Label>
        <Select value={status} onValueChange={(v) => setStatus(v as ComplaintStatus)}>
          <SelectTrigger id="complaint-status" className="h-11 w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {COMPLAINT_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {statusLabel(s)}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <FormError error={update.error} />
      <Button className="h-11" disabled={update.isPending || status === complaint.status} onClick={() => void save()}>
        {update.isPending && <Loader2 className="animate-spin" aria-hidden />}
        Update status
      </Button>
    </>
  );
}
