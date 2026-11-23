/** Post / edit a notice in a drawer: bottom sheet on phones, right side from 640px. */
import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Field, PickField, ServerError } from "@/features/connections/fields";
import type { Area } from "@/features/connections/reference";
import { useIsMobile } from "@/features/connections/useIsMobile";
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { type Notice, useSaveNotice } from "./api";
import { dhakaLocalFromNow, dhakaLocalToIso, isoToDhakaLocal } from "./dhaka";

// Mirrors NoticeCreate in /openapi.json. Times are "YYYY-MM-DDTHH:mm" strings, so plain string order is time order.
const schema = z
  .object({
    area_id: z.string().min(1, "Choose an area."),
    kind: z.enum(["outage", "maintenance"]),
    message_bn: z.string().trim().min(1, "Write the Bangla message.").max(500, "Use 500 characters or fewer."),
    message_en: z.string().trim().min(1, "Write the English message.").max(500, "Use 500 characters or fewer."),
    starts_at: z.string().min(1, "Choose when it starts."),
    ends_at: z.string().min(1, "Choose when it ends."),
  })
  .refine((v) => !v.starts_at || !v.ends_at || v.ends_at > v.starts_at, { path: ["ends_at"], message: "The end must be after the start." });
type Values = z.infer<typeof schema>;
const FIELDS = ["area_id", "kind", "message_bn", "message_en", "starts_at", "ends_at"] as const;

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** null = post a new notice. */
  notice: Notice | null;
  areas: Area[];
}

export function NoticeSheet({ open, onOpenChange, notice, areas }: Props) {
  const mobile = useIsMobile();
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side={mobile ? "bottom" : "right"} className="max-h-[92dvh] overflow-y-auto sm:max-h-none sm:max-w-md">
        <SheetHeader>
          <SheetTitle>{notice ? "Edit notice" : "Post a notice"}</SheetTitle>
          <SheetDescription>Times are in Bangladesh time (UTC+6).</SheetDescription>
        </SheetHeader>
        <NoticeForm notice={notice} areas={areas} onDone={() => onOpenChange(false)} />
      </SheetContent>
    </Sheet>
  );
}

function NoticeForm({ notice, areas, onDone }: Omit<Props, "open" | "onOpenChange"> & { onDone: () => void }) {
  const save = useSaveNotice();
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: {
      area_id: notice ? String(notice.area_id) : "",
      kind: notice?.kind ?? "outage",
      message_bn: notice?.message_bn ?? "",
      message_en: notice?.message_en ?? "",
      starts_at: notice ? isoToDhakaLocal(notice.starts_at) : dhakaLocalFromNow(0),
      ends_at: notice ? isoToDhakaLocal(notice.ends_at) : dhakaLocalFromNow(2),
    },
  });
  const { errors } = form.formState;

  const onSubmit = form.handleSubmit(async (v) => {
    const body = {
      ...v,
      area_id: Number(v.area_id),
      starts_at: dhakaLocalToIso(v.starts_at),
      ends_at: dhakaLocalToIso(v.ends_at),
    };
    try {
      await save.mutateAsync(notice ? { id: notice.id, body } : { id: null, body });
      toast.success(notice ? "Notice saved." : "Notice posted.");
      onDone();
    } catch (e) {
      // Keep everything typed; show 422 messages under their inputs.
      if (e instanceof ApiError) {
        const fe = fieldErrors(e);
        FIELDS.forEach((f) => fe[f] && form.setError(f, { message: fe[f] }));
      }
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4 px-4 pb-4">
      <PickField name="area_id" label="Area" control={form.control} error={errors.area_id?.message} options={areas.map((a) => ({ value: String(a.id), label: a.name }))} />
      <PickField name="kind" label="Kind" control={form.control} error={errors.kind?.message} options={[{ value: "outage", label: "Outage" }, { value: "maintenance", label: "Maintenance" }]} />
      <Field id="message_bn" label="Message in Bangla" error={errors.message_bn?.message}>
        <Textarea id="message_bn" lang="bn" rows={3} aria-invalid={!!errors.message_bn} {...form.register("message_bn")} />
      </Field>
      <Field id="message_en" label="Message in English" error={errors.message_en?.message}>
        <Textarea id="message_en" lang="en" rows={3} aria-invalid={!!errors.message_en} {...form.register("message_en")} />
      </Field>
      <Field id="starts_at" label="Starts" error={errors.starts_at?.message}>
        <Input id="starts_at" type="datetime-local" className="h-11" aria-invalid={!!errors.starts_at} {...form.register("starts_at")} />
      </Field>
      <Field id="ends_at" label="Ends" error={errors.ends_at?.message}>
        <Input id="ends_at" type="datetime-local" className="h-11" aria-invalid={!!errors.ends_at} {...form.register("ends_at")} />
      </Field>
      <ServerError error={save.error} />
      <Button type="submit" className="h-11 w-full" disabled={save.isPending}>
        {save.isPending && <Loader2 className="animate-spin" aria-hidden />}
        {notice ? "Save notice" : "Post notice"}
      </Button>
    </form>
  );
}
