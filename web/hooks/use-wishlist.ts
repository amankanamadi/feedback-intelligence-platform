import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { WishlistRead } from "@/types/wishlist";

export function useWishlist() {
  return useQuery<WishlistRead[]>({
    queryKey: ["wishlist"],
    queryFn: () => apiFetch<WishlistRead[]>("/wishlist"),
  });
}

export function useAddToWishlistMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (propertyId: number) => apiFetch<WishlistRead>(`/wishlist/${propertyId}`, { method: "POST" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });
}

export function useRemoveFromWishlistMutation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (propertyId: number) => apiFetch<void>(`/wishlist/${propertyId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["wishlist"] });
    },
  });
}
