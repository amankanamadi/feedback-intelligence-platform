"use client";

import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Building2, MapPin, MessageSquareText, Star } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { DetailSkeleton, TableSkeleton } from "@/components/shared/LoadingSkeletons";
import { StatusBadge } from "@/components/shared/StatusBadge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { usePropertyDetail } from "@/hooks/use-property-detail";
import { useIsGuest } from "@/hooks/use-is-guest";
import { useIsHost } from "@/hooks/use-is-host";
import { usePropertyFeedbackHistory } from "@/hooks/use-property-feedback-history";
import { useWishlist, useAddToWishlistMutation, useRemoveFromWishlistMutation } from "@/hooks/use-wishlist";
import { isApiError } from "@/lib/auth";
import { formatDate } from "@/lib/format";

export default function PropertyDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);
  const query = usePropertyDetail(id);
  const isGuest = useIsGuest();
  const isHost = useIsHost();
  const wishlistQuery = useWishlist();
  const addMutation = useAddToWishlistMutation();
  const removeMutation = useRemoveFromWishlistMutation();
  // Only ever attempted for a host, and the backend 403s outright if they
  // don't own this particular property - silently hidden below rather
  // than shown as an error, since "not my listing" is a completely normal
  // thing for a host to be looking at (they can browse every property,
  // same as anyone else).
  const historyQuery = usePropertyFeedbackHistory(id, { enabled: isHost && Number.isFinite(id) });
  const showHistory = isHost && !historyQuery.isError;

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
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-6">
          <Card className="w-full max-w-xl">
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

          {showHistory && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Feedback history</CardTitle>
              </CardHeader>
              <CardContent>
                <DataState
                  query={historyQuery}
                  skeleton={<TableSkeleton rows={3} />}
                  empty={(data) => data.length === 0}
                  emptyState={
                    <EmptyState
                      icon={<MessageSquareText className="size-10" aria-hidden="true" />}
                      title="No feedback yet"
                      description="Reviews and complaints about this property will show up here."
                    />
                  }
                >
                  {(items) => (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>Feedback</TableHead>
                          <TableHead>Category</TableHead>
                          <TableHead>Status</TableHead>
                          <TableHead>Date</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {items.map((item) => (
                          <TableRow key={item.id}>
                            <TableCell className="max-w-sm truncate">{item.raw_text}</TableCell>
                            <TableCell className="text-muted-foreground">{item.main_category ?? "—"}</TableCell>
                            <TableCell>
                              <StatusBadge status={item.status} />
                            </TableCell>
                            <TableCell className="text-muted-foreground">{formatDate(item.created_at)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </DataState>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </DataState>
  );
}
