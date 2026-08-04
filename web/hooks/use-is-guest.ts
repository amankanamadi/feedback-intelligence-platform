import { useAuth } from "@/lib/auth";

export function useIsGuest(): boolean {
  const { user } = useAuth();
  return user?.role === "GUEST";
}
