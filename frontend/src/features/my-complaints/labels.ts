import type { Schemas } from "@/api/types";

export const CATEGORY_LABEL: Record<Schemas["ComplaintCreate"]["category"], string> = {
  no_internet: "No internet",
  slow_speed: "Slow speed",
  billing: "Billing",
  other: "Other",
};

export const CATEGORIES = Object.keys(CATEGORY_LABEL) as Schemas["ComplaintCreate"]["category"][];

/** The API sends category as a plain string; fall back to the raw word if it is new. */
export function categoryLabel(category: string): string {
  return (CATEGORY_LABEL as Record<string, string>)[category] ?? category;
}
