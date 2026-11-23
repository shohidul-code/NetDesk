/** Small form pieces the connection and notice drawers share. */
import type { ReactNode } from "react";
import { type Control, Controller, type FieldValues, type Path } from "react-hook-form";
import { ApiError, fieldErrors } from "@/api/errors";
import { FormError } from "@/components/states";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

export function Field({ id, label, error, children }: { id: string; label: string; error?: string; children: ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {error && <p className="text-sm text-danger">{error}</p>}
    </div>
  );
}

interface PickProps<T extends FieldValues> {
  name: Path<T>;
  label: string;
  control: Control<T>;
  error?: string;
  options: { value: string; label: string }[];
}

/** A labelled Select wired to react-hook-form; the form holds the option's string value. */
export function PickField<T extends FieldValues>({ name, label, control, error, options }: PickProps<T>) {
  return (
    <Field id={name} label={label} error={error}>
      <Controller
        name={name}
        control={control}
        render={({ field }) => (
          <Select value={String(field.value ?? "")} onValueChange={field.onChange}>
            <SelectTrigger id={name} className="h-11 w-full" aria-invalid={!!error}>
              <SelectValue placeholder={`Choose ${label.toLowerCase()}`} />
            </SelectTrigger>
            <SelectContent>
              {options.map((o) => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      />
    </Field>
  );
}

/** True when a 422 came back with messages for specific inputs (they show under those inputs). */
function hasFieldErrors(error: unknown): boolean {
  return error instanceof ApiError && Object.keys(fieldErrors(error)).length > 0;
}

/** A form-level error. A 422 with no field (for example "end must be after start") shows the server's sentence. */
export function ServerError({ error }: { error: unknown }) {
  if (!error || hasFieldErrors(error)) return null;
  if (error instanceof ApiError && error.status === 422 && error.message) {
    return (
      <p role="alert" className="text-sm text-danger">
        {error.message}
      </p>
    );
  }
  return <FormError error={error} />;
}
