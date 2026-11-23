/** Create / edit drawer: bottom sheet on phones, right side from 640px (UI.md §5). */
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { type Connection, useSaveConnection } from "./api";
import { Field, PickField, ServerError } from "./fields";
import type { Area, Package } from "./reference";
import { useIsMobile } from "./useIsMobile";

// Mirrors ConnectionCreate in /openapi.json; the API still has the last word (phone format is checked there).
const schema = z.object({
  customer_code: z.string().trim().regex(/^ND-\d{6}$/, "Use the format ND-000123."),
  customer_name: z.string().trim().min(2, "Enter at least 2 characters.").max(120, "Use 120 characters or fewer."),
  phone: z.string().trim().min(1, "Enter a phone number."),
  address: z.string().trim().max(300, "Use 300 characters or fewer."),
  area_id: z.string().min(1, "Choose an area."),
  package_id: z.string().min(1, "Choose a package."),
  status: z.enum(["active", "suspended", "disconnected"]),
});
type Values = z.infer<typeof schema>;
const FIELDS = Object.keys(schema.shape) as (keyof Values)[];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** null = create. */
  connection: Connection | null;
  areas: Area[];
  packages: Package[];
}

export function ConnectionSheet({ open, onOpenChange, connection, areas, packages }: Props) {
  const mobile = useIsMobile();
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={mobile ? "bottom" : "right"} className="max-h-[92dvh] overflow-y-auto sm:max-h-none sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{connection ? `Edit ${connection.customer_code}` : "New connection"}</SheetTitle>
          <SheetDescription>{connection ? "Change the details, then save." : "Add a customer to the network."}</SheetDescription>
        </SheetHeader>
        <ConnectionForm connection={connection} areas={areas} packages={packages} onDone={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}

function ConnectionForm({ connection, areas, packages, onDone }: Omit<Props, "open" | "onOpenChange"> & { onDone: () => void }) {
  const save = useSaveConnection();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      customer_code: connection?.customer_code ?? "",
      customer_name: connection?.customer_name ?? "",
      phone: connection?.phone ?? "",
      address: connection?.address ?? "",
      area_id: connection ? String(connection.area_id) : "",
      package_id: connection ? String(connection.package_id) : "",
      status: (connection?.status as Values["status"] | undefined) ?? "active",
    },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(async (v) => {
    const { customer_code, ...rest } = v;
    const body = { ...rest, area_id: Number(v.area_id), package_id: Number(v.package_id) };
    try {
      await save.mutateAsync(connection ? { id: connection.id, body } : { id: null, body: { ...body, customer_code } });
      toast.success(connection ? "Connection saved." : "Connection created.");
      onDone();
    } catch (e) {
      // Keep everything typed; show 422 messages under their inputs.
      if (e instanceof ApiError) {
        const fe = fieldErrors(e);
        FIELDS.forEach((f) => fe[f] && form.setError(f, { message: fe[f] }));
      }
    }
  });

  const err = save.error instanceof ApiError ? save.error : null;
  const duplicate = err?.status === 409; // shown beside the code input

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4 px-4 pb-4">
      <Field id="customer_code" label="Customer code" error={duplicate ? err.message : errors.customer_code?.message}>
        <Input id="customer_code" placeholder="ND-000123" readOnly={!!connection} className="read-only:bg-bg" aria-invalid={!!errors.customer_code || duplicate} {...form.register("customer_code")} />
      </Field>
      <Field id="customer_name" label="Customer name" error={errors.customer_name?.message}>
        <Input id="customer_name" autoComplete="off" aria-invalid={!!errors.customer_name} {...form.register("customer_name")} />
      </Field>
      <Field id="phone" label="Phone" error={errors.phone?.message}>
        <Input id="phone" type="tel" placeholder="01712345678" aria-invalid={!!errors.phone} {...form.register("phone")} />
      </Field>
      <Field id="address" label="Address" error={errors.address?.message}>
        <Input id="address" aria-invalid={!!errors.address} {...form.register("address")} />
      </Field>
      <PickField name="area_id" label="Area" control={form.control} error={errors.area_id?.message} options={areas.map((a) => ({ value: String(a.id), label: a.name }))} />
      <PickField name="package_id" label="Package" control={form.control} error={errors.package_id?.message} options={packages.map((p) => ({ value: String(p.id), label: p.name }))} />
      <PickField name="status" label="Status" control={form.control} error={errors.status?.message} options={["active", "suspended", "disconnected"].map((s) => ({ value: s, label: s.charAt(0).toUpperCase() + s.slice(1) }))} />
      {!duplicate && <ServerError error={save.error} />}
      <Button type="submit" className="h-11 w-full" disabled={save.isPending}>
        {save.isPending && <Loader2 className="animate-spin" aria-hidden />}
        {connection ? "Save changes" : "Create connection"}
      </Button>
    </form>
  );
}

