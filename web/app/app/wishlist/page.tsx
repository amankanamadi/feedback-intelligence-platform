"use client";

import Link from "next/link";
import { toast } from "sonner";
import { Heart } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton } from "@/components/shared/LoadingSkeletons";
import { PropertyCard } from "@/components/property/PropertyCard";
import { useWishlist, useRemoveFromWishlistMutation } from "@/hooks/use-wishlist";
import { isApiError } from "@/lib/auth";

export default function WishlistPage() {
  const wishlistQuery = useWishlist();
  const removeMutation = useRemoveFromWishlistMutation();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">My Wishlist</h1>
        <p className="text-muted-foreground">Properties you've saved for later.</p>
      </div>

      <DataState
        query={wishlistQuery}
        skeleton={<ListSkeleton rows={3} />}
        empty={(data) => data.length === 0}
        emptyState={
          <EmptyState
            icon={<Heart className="size-10" aria-hidden="true" />}
            title="Nothing saved yet"
            description="Browse properties and tap the heart icon to save one here."
          />
        }
      >
        {(items) => (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {items.map((item) => (
              <Link key={item.id} href={`/app/properties/${item.property.id}`}>
                <PropertyCard
                  property={item.property}
                  isWishlisted
                  onToggleWishlist={() =>
                    removeMutation.mutate(item.property.id, {
                      onError: (error) =>
                        toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
                    })
                  }
                />
              </Link>
            ))}
          </div>
        )}
      </DataState>
    </div>
  );
}
