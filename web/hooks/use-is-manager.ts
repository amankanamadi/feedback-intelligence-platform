import { useAuth } from "@/lib/auth";
import { MANAGE_ROLES } from "@/types/auth";

export function useIsManager(): boolean {
  const { user } = useAuth();
  return !!user && MANAGE_ROLES.includes(user.role);
}
