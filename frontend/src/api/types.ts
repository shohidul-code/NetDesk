/** Friendly names for the generated OpenAPI types. Never write API shapes by hand. */
import type { components } from "./schema";

export type Schemas = components["schemas"];
export type User = Schemas["UserRead"];
export type Role = "customer" | "technician" | "admin";
