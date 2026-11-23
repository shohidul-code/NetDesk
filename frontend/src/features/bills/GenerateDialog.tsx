import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Field, ServerError } from "@/features/connections/fields";
import { currentPeriod } from "@/features/notices/dhaka";
import { formatMonth } from "@/lib/format";
import { useGenerateBills } from "./api";

// Mirrors GenerateBills.period in /openapi.json.
const schema = z.object({ period: z.string().regex(/^\d{4}-(0[1-9]|1[0-2])$/, "Choose a month, like 2026-12.") });
type Values = z.infer<typeof schema>;

export function GenerateDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>{open && <GenerateBody onClose={() => onOpenChange(false)} />}</DialogContent>
    </Dialog>
  );
}

function GenerateBody({ onClose }: { onClose: () => void }) {
  const generate = useGenerateBills();
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { period: currentPeriod() } });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(async ({ period }) => {
    try {
      await generate.mutateAsync(period);
    } catch (e) {
      if (e instanceof ApiError) {
        const fe = fieldErrors(e);
        if (fe.period) form.setError("period", { message: fe.period });
      }
    }
  });

  const result = generate.data;
  return (
    <>
      <DialogHeader>
        <DialogTitle>Generate bills for a month</DialogTitle>
        <DialogDescription>Adds one bill for each active connection. Months that already have a bill are skipped.</DialogDescription>
      </DialogHeader>
      <form onSubmit={onSubmit} noValidate className="space-y-4">
        <Field id="gen-period" label="Month" error={errors.period?.message}>
          <Input id="gen-period" type="month" placeholder="YYYY-MM" className="h-11" aria-invalid={!!errors.period} {...form.register("period")} />
        </Field>
        <ServerError error={generate.error} />
        {result && (
          <p role="status" className="rounded-md bg-success/10 p-3 text-sm text-success">
            {formatMonth(result.period)}: <span className="tabular">{result.created}</span> created, <span className="tabular">{result.skipped}</span> skipped.
          </p>
        )}
        <Button type="submit" className="h-11 w-full" disabled={generate.isPending}>
          {generate.isPending && <Loader2 className="animate-spin" aria-hidden />}
          Generate bills
        </Button>
        {result && (
          <Button type="button" variant="outline" className="h-11 w-full" onClick={onClose}>
            Done
          </Button>
        )}
      </form>
    </>
  );
}
