import { MapPin, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { Property } from "@/types/feedback";

export function PropertyCard({ property }: { property: Property }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{property.name}</CardTitle>
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
