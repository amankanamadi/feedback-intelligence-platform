export type Role =
  | "GUEST"
  | "HOST"
  | "SUPPORT_MANAGER"
  | "OPS_MANAGER"
  | "PRODUCT_MANAGER"
  | "TRUST_SAFETY"
  | "EXEC";

// Submitter tier - self-registered, scoped to their own feedback.
export const SUBMITTER_ROLES: Role[] = ["GUEST", "HOST"];
// Staff tier - provisioned by manual promotion, can view all feedback/analytics/reports.
export const STAFF_ROLES: Role[] = ["SUPPORT_MANAGER", "OPS_MANAGER", "PRODUCT_MANAGER", "TRUST_SAFETY", "EXEC"];
// Subset of staff that can also edit cases, bulk-upload, and export. TRUST_SAFETY
// is staff-tier but not manager-tier - it gets its own scoped write path on the
// backend for items routed to it, not general manager power.
export const MANAGE_ROLES: Role[] = ["SUPPORT_MANAGER", "OPS_MANAGER"];

export const ROLE_LABELS: Record<Role, string> = {
  GUEST: "Guest",
  HOST: "Host",
  SUPPORT_MANAGER: "Customer Support Manager",
  OPS_MANAGER: "Operations Manager",
  PRODUCT_MANAGER: "Product Manager",
  TRUST_SAFETY: "Trust & Safety",
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
