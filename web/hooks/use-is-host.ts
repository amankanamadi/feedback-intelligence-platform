import { useAuth } from "@/lib/auth";

export function useIsHost(): boolean {
  const { user } = useAuth();
  return user?.role === "HOST";
}
