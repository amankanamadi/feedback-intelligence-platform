import { Heart, MapPin, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import type { Property } from "@/types/feedback";

export function PropertyCard({
  property,
  isWishlisted,
  onToggleWishlist,
}: {
  property: Property;
  isWishlisted?: boolean;
  onToggleWishlist?: () => void;
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-2 space-y-0">
        <CardTitle className="text-base">{property.name}</CardTitle>
        {onToggleWishlist && (
          <button
            type="button"
            onClick={(e) => {
              // PropertyCard is sometimes wrapped in a Link (the browsing
              // grid) - stop the click from also triggering navigation.
              e.preventDefault();
              e.stopPropagation();
              onToggleWishlist();
            }}
            aria-label={isWishlisted ? "Remove from wishlist" : "Add to wishlist"}
          >
            <Heart
              className={cn("size-5", isWishlisted ? "fill-destructive text-destructive" : "text-muted-foreground")}
            />
          </button>
        )}
      </CardHeader>
      <CardContent className="flex flex-col gap-2 text-sm text-muted-foreground">
        <p className="flex items-center gap-1.5">
          <MapPin className="size-4" aria-hidden="true" />
          {property.city}, {property.country}
        </p>
        <p>{property.property_type}</p>
        {property.average_rating !== null && (
          <p className="flex items-center gap-1.5 font-medium text-foreground">
            <Star className="size-4 fill-amber-400 text-amber-400" aria-hidden="true" />
            {property.average_rating.toFixed(1)}
          </p>
        )}
      </CardContent>
    </Card>
  );
}
