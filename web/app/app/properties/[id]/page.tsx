"use client";

import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Building2, MapPin, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/DataState";
import { DetailSkeleton } from "@/components/shared/LoadingSkeletons";
import { EmptyState } from "@/components/shared/EmptyState";
import { usePropertyDetail } from "@/hooks/use-property-detail";
import { useIsGuest } from "@/hooks/use-is-guest";
import { useWishlist, useAddToWishlistMutation, useRemoveFromWishlistMutation } from "@/hooks/use-wishlist";
import { isApiError } from "@/lib/auth";

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = usePropertyDetail(id);
  const isGuest = useIsGuest();
  const wishlistQuery = useWishlist();
  const addMutation = useAddToWishlistMutation();
  const removeMutation = useRemoveFromWishlistMutation();

  if (!Number.isFinite(id)) {
    return (
      <EmptyState
        icon={<Building2 className="size-10" aria-hidden="true" />}
        title="Property not found"
        description="That doesn't look like a valid property link."
      />
    );
  }

  const isWishlisted = (wishlistQuery.data ?? []).some((item) => item.property.id === id);

  const handleToggle = () => {
    const mutation = isWishlisted ? removeMutation : addMutation;
    mutation.mutate(id, {
      onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
    });
  };

  return (
    <DataState query={query} skeleton={<DetailSkeleton />}>
      {(property) => (
        <Card className="mx-auto w-full max-w-xl">
          <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
            <CardTitle>{property.name}</CardTitle>
            {isGuest && (
              <Button
                variant={isWishlisted ? "default" : "outline"}
                size="sm"
                onClick={handleToggle}
                isLoading={addMutation.isPending || removeMutation.isPending}
              >
                {isWishlisted ? "Saved" : "Add to wishlist"}
              </Button>
            )}
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm">
            <p className="flex items-center gap-1.5 text-muted-foreground">
              <MapPin className="size-4" aria-hidden="true" />
              {property.city}, {property.country}
            </p>
            <p className="text-muted-foreground">{property.property_type}</p>
            <p className="text-muted-foreground">Hosted by {property.host_name}</p>
            {property.average_rating !== null && (
              <p className="flex items-center gap-1.5 font-medium text-foreground">
                <Star className="size-4 fill-amber-400 text-amber-400" aria-hidden="true" />
                {property.average_rating.toFixed(1)} average rating
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </DataState>
  );
}
