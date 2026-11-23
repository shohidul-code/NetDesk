import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Field, PickField, ServerError } from "@/features/connections/fields";
import { formatMoney, formatMonth } from "@/lib/format";
import { type Bill, PAYMENT_METHODS, useRecordPayment } from "./api";

// Mirrors PaymentCreate in /openapi.json.
const schema = z.object({
  trx_id: z.string().trim().min(4, "Enter at least 4 characters.").max(40, "Use 40 characters or fewer."),
  payment_method: z.enum(["bkash", "nagad", "cash", "bank"], "Choose how it was paid."),
});
type Values = z.infer<typeof schema>;

interface Props {
  bill: Bill | null;
  /** The customer code, so the dialog names who is paying. */
  customer: string;
  onClose: () => void;
}

export function PaymentDialog({ bill, customer, onClose }: Props) {
  return (
    <Dialog open={bill !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>{bill && <PaymentForm key={bill.id} bill={bill} customer={customer} onClose={onClose} />}</DialogContent>
    </Dialog>
  );
}

function PaymentForm({ bill, customer, onClose }: Props & { bill: Bill }) {
  const pay = useRecordPayment();
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { trx_id: "", payment_method: "bkash" } });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(async (body) => {
    try {
      await pay.mutateAsync({ billId: bill.id, body });
      toast.success("Payment verified.");
      onClose();
    } catch (e) {
      // Input stays. 422: under the inputs. 409 (TrxID reused, already paid): shown below as the server's sentence.
      if (e instanceof ApiError) {
        const fe = fieldErrors(e);
        if (fe.trx_id) form.setError("trx_id", { message: fe.trx_id });
        if (fe.payment_method) form.setError("payment_method", { message: fe.payment_method });
      }
    }
  });

  return (
    <>
      <DialogHeader>
        <DialogTitle>Verify payment</DialogTitle>
        <DialogDescription>
          {customer} · {formatMonth(bill.period)} · {formatMoney(bill.amount_bdt)}
        </DialogDescription>
      </DialogHeader>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field id="trx_id" label="TrxID" error={errors.trx_id?.message}>
          <Input id="trx_id" autoComplete="off" className="h-11" aria-invalid={!!errors.trx_id} {...form.register("trx_id")} />
        </Field>
        <PickField name="payment_method" label="Paid by" control={form.control} error={errors.payment_method?.message} options={PAYMENT_METHODS} />
        <ServerError error={pay.error} />
        <Button type="submit" className="h-11 w-full" disabled={pay.isPending}>
          {pay.isPending && <Loader2 className="animate-spin" aria-hidden />}
          Verify payment
        </Button>
      </form>
    </>
  );
}
