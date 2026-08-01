export type Role = "GUEST" | "HOST" | "SUPPORT_MANAGER" | "OPS_MANAGER" | "PRODUCT_MANAGER" | "EXEC";

// Submitter tier - self-registered, scoped to their own feedback.
export const SUBMITTER_ROLES: Role[] = ["GUEST", "HOST"];
// Staff tier - provisioned by manual promotion, can view all feedback/analytics/reports.
export const STAFF_ROLES: Role[] = ["SUPPORT_MANAGER", "OPS_MANAGER", "PRODUCT_MANAGER", "EXEC"];
// Subset of staff that can also edit cases, bulk-upload, and export.
export const MANAGE_ROLES: Role[] = ["SUPPORT_MANAGER", "OPS_MANAGER"];

export const ROLE_LABELS: Record<Role, string> = {
  GUEST: "Guest",
  HOST: "Host",
  SUPPORT_MANAGER: "Customer Support Manager",
  OPS_MANAGER: "Operations Manager",
  PRODUCT_MANAGER: "Product Manager",
  EXEC: "Executive Leadership",
};

export type Me = {
  id: number;
  email: string;
  full_name: string | null;
  role: Role;
  is_active: boolean;
  created_at: string;
};
