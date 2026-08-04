import { useAuth } from "@/lib/auth";
import { STAFF_ROLES } from "@/types/auth";

export function useIsStaff(): boolean {
  const { user } = useAuth();
  return !!user && STAFF_ROLES.includes(user.role);
}
