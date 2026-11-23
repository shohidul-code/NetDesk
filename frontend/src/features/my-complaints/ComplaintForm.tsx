import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useState } from "react";
import { Controller, useForm, useWatch } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";
import { ApiError, fieldErrors } from "@/api/errors";
import { FormError } from "@/components/states";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import { useMyConnection } from "@/features/customer-home/queries";
import { CATEGORIES, CATEGORY_LABEL } from "./labels";
import { useCreateComplaint } from "./queries";

const MAX = 1000;
const schema = z.object({
  category: z.enum(CATEGORIES, { error: "Choose what is wrong." }),
  description: z.string().trim().min(1, "Describe the problem.").max(MAX, `Use at most ${MAX} characters.`),
});
type Values = z.infer<typeof schema>;

export function ComplaintForm() {
  const connection = useMyConnection();
  const create = useCreateComplaint();
  const [error, setError] = useState<unknown>(null);
  const form = useForm<Values>({ resolver: zodResolver(schema), defaultValues: { description: "" } });
  const { errors } = form.formState;
  const length = useWatch({ control: form.control, name: "description" }).length;

  const onSubmit = form.handleSubmit(async (values) => {
    const connectionId = connection.data?.id;
    if (!connectionId) return;
    setError(null);
    try {
      await create.mutateAsync({ ...values, connection_id: connectionId });
      toast.success("Complaint sent. We will update its status here.");
      form.reset({ description: "" });
    } catch (e) {
      if (e instanceof ApiError && e.status === 422) {
        for (const [field, message] of Object.entries(fieldErrors(e))) {
          if (field === "category" || field === "description") form.setError(field, { message });
        }
      }
      setError(e); // the typed text stays in the form
    }
  });

  return (
    <form onSubmit={onSubmit} noValidate className="space-y-4">
      <div className="space-y-1.5">
        <Label htmlFor="category">What is wrong?</Label>
        <Controller
          control={form.control}
          name="category"
          render={({ field }) => (
            <Select value={field.value ?? ""} onValueChange={field.onChange}>
              <SelectTrigger id="category" className="h-11 w-full" aria-invalid={!!errors.category}>
                <SelectValue placeholder="Choose a category" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c} value={c}>
                    {CATEGORY_LABEL[c]}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}
        />
        {errors.category && <p className="text-sm text-danger">{errors.category.message}</p>}
      </div>
      <div className="space-y-1.5">
        <Label htmlFor="description">Description</Label>
        <Textarea id="description" rows={4} aria-invalid={!!errors.description} {...form.register("description")} />
        <div className="flex justify-between gap-2 text-sm">
          <span className="text-danger">{errors.description?.message}</span>
          <span className={length > MAX ? "text-danger" : "text-text-muted"}>
            {length}/{MAX}
          </span>
        </div>
      </div>
      <ComplaintError error={error} />
      <Button type="submit" className="h-11 w-full sm:w-auto" disabled={create.isPending || !connection.data}>
        {create.isPending && <Loader2 className="animate-spin" aria-hidden />}
        Send complaint
      </Button>
    </form>
  );
}

function ComplaintError({ error }: { error: unknown }) {
  if (error instanceof ApiError && error.status === 403)
    return (
      <p role="alert" className="text-sm text-danger">
        Complaints are taken by your operator for now.
      </p>
    );
  return <FormError error={error} />;
}
