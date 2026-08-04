"use client";

import { useState } from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Input } from "@/components/ui/input";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton } from "@/components/shared/LoadingSkeletons";
import { PropertyCard } from "@/components/property/PropertyCard";
import { useProperties } from "@/hooks/use-properties";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useIsGuest } from "@/hooks/use-is-guest";
import { useWishlist, useAddToWishlistMutation, useRemoveFromWishlistMutation } from "@/hooks/use-wishlist";
import { isApiError } from "@/lib/auth";
import { Building2 } from "lucide-react";

export default function PropertiesPage() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search, 300);
  const propertiesQuery = useProperties(debouncedSearch || undefined);
  const isGuest = useIsGuest();
  const wishlistQuery = useWishlist();
  const addMutation = useAddToWishlistMutation();
  const removeMutation = useRemoveFromWishlistMutation();

  const wishlistedIds = new Set((wishlistQuery.data ?? []).map((item) => item.property.id));

  const handleToggle = (propertyId: number) => {
    const mutation = wishlistedIds.has(propertyId) ? removeMutation : addMutation;
    mutation.mutate(propertyId, {
      onError: (error) => toast.error(isApiError(error) ? error.message : "Something went wrong. Please try again."),
    });
  };

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Properties</h1>
        <p className="text-muted-foreground">Browse listings across the platform.</p>
      </div>

      <Input
        placeholder="Search by name, city, or country..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="max-w-sm"
      />

      <DataState
        query={propertiesQuery}
        skeleton={<ListSkeleton rows={4} />}
        empty={(data) => data.length === 0}
        emptyState={
          <EmptyState
            icon={<Building2 className="size-10" aria-hidden="true" />}
            title="No properties found"
            description="Try a different search."
          />
        }
      >
        {(properties) => (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {properties.map((property) => (
              <Link key={property.id} href={`/app/properties/${property.id}`}>
                <PropertyCard
                  property={property}
                  isWishlisted={isGuest ? wishlistedIds.has(property.id) : undefined}
                  onToggleWishlist={isGuest ? () => handleToggle(property.id) : undefined}
                />
              </Link>
            ))}
          </div>
        )}
      </DataState>
    </div>
  );
}
