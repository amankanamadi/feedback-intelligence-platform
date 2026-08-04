import { useAuth } from "@/lib/auth";

export function useIsTrustSafety(): boolean {
  const { user } = useAuth();
  return user?.role === "TRUST_SAFETY";
}
