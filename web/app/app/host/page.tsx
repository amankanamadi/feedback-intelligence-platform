"use client";

import { useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { StatusBadge, PriorityBadge } from "@/components/shared/StatusBadge";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { ListSkeleton, TableSkeleton } from "@/components/shared/LoadingSkeletons";
import { Skeleton } from "@/components/ui/skeleton";
import { PropertyCard } from "@/components/property/PropertyCard";
import { RespondDialog } from "@/components/host/RespondDialog";
import { useHostProperties } from "@/hooks/use-host-properties";
import { useHostPerformance } from "@/hooks/use-host-performance";
import { useHostQueue } from "@/hooks/use-host-queue";
import { useHostReviews } from "@/hooks/use-host-reviews";
import { formatDate } from "@/lib/format";
import { Home, Inbox, MessageSquareHeart, Star } from "lucide-react";

export default function HostDashboardPage() {
  const propertiesQuery = useHostProperties();
  const performanceQuery = useHostPerformance();
  const [unresolvedOnly, setUnresolvedOnly] = useState(true);
  const queueQuery = useHostQueue(undefined, unresolvedOnly);
  const reviewsQuery = useHostReviews();

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Host Dashboard</h1>
        <p className="text-muted-foreground">Your properties, performance, and complaints that need your attention.</p>
      </div>

      <DataState
        query={performanceQuery}
        skeleton={<Skeleton className="h-32 w-full" />}
        empty={(data) => data === null}
        emptyState={
          <EmptyState
            icon={<Home className="size-10" aria-hidden="true" />}
            title="No properties assigned yet"
            description="Once you have a listing, your performance score will show up here."
          />
        }
      >
        {(performance) => (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Performance score</CardTitle>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <div>
                <p className="text-2xl font-semibold text-foreground">{performance!.performance_score}</p>
                <p className="text-xs text-muted-foreground">Performance score</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-foreground">{performance!.feedback_count}</p>
                <p className="text-xs text-muted-foreground">Feedback received</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-foreground">
                  {performance!.avg_guest_rating ?? "—"}
                </p>
                <p className="text-xs text-muted-foreground">Avg. guest rating</p>
              </div>
              <div>
                <p className="text-2xl font-semibold text-foreground">{performance!.open_critical_count}</p>
                <p className="text-xs text-muted-foreground">Open critical cases</p>
              </div>
            </CardContent>
          </Card>
        )}
      </DataState>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-foreground">Your properties</h2>
        <DataState
          query={propertiesQuery}
          skeleton={<ListSkeleton rows={2} />}
          empty={(data) => data.length === 0}
          emptyState={
            <EmptyState
              icon={<Home className="size-10" aria-hidden="true" />}
              title="No properties assigned yet"
              description="Properties assigned to you will appear here as cards."
            />
          }
        >
          {(properties) => (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {properties.map((property) => (
                <PropertyCard key={property.id} property={property} />
              ))}
            </div>
          )}
        </DataState>
      </div>

      <div>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-lg font-semibold text-foreground">Complaint queue</h2>
          <label className="flex items-center gap-2 text-sm text-foreground">
            <input
              type="checkbox"
              checked={unresolvedOnly}
              onChange={(e) => setUnresolvedOnly(e.target.checked)}
            />
            Unresolved only
          </label>
        </div>
        <DataState
          query={queueQuery}
          skeleton={<TableSkeleton rows={4} />}
          empty={(data) => data.length === 0}
          emptyState={
            <EmptyState
              icon={<Inbox className="size-10" aria-hidden="true" />}
              title={unresolvedOnly ? "Nothing open right now" : "Nothing routed to you yet"}
              description={
                unresolvedOnly
                  ? "Resolved and closed cases are hidden - uncheck \"Unresolved only\" to see your full history."
                  : "Complaints assigned to your properties will show up here."
              }
            />
          }
        >
          {(items) => (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feedback</TableHead>
                  <TableHead>Property</TableHead>
                  <TableHead>Category</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>SLA</TableHead>
                  <TableHead />
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="max-w-xs truncate">{item.raw_text}</TableCell>
                    <TableCell className="text-muted-foreground">
                      {item.property_id ? (
                        <Link href={`/app/properties/${item.property_id}`} className="hover:underline">
                          {item.property_name ?? "—"}
                        </Link>
                      ) : (
                        item.property_name ?? "—"
                      )}
                    </TableCell>
                    <TableCell>{item.sub_category ?? "—"}</TableCell>
                    <TableCell>{item.priority ? <PriorityBadge priority={item.priority} /> : "—"}</TableCell>
                    <TableCell>
                      <StatusBadge status={item.status} />
                    </TableCell>
                    <TableCell>
                      {item.sla_breached && <Badge variant="destructive">SLA Breached</Badge>}
                    </TableCell>
                    <TableCell>
                      <RespondDialog feedback={item} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DataState>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-foreground">Recent guest reviews</h2>
        <p className="mb-3 text-sm text-muted-foreground">
          What guests said after their stay - informational only, no response needed.
        </p>
        <DataState
          query={reviewsQuery}
          skeleton={<TableSkeleton rows={3} />}
          empty={(data) => data.length === 0}
          emptyState={
            <EmptyState
              icon={<MessageSquareHeart className="size-10" aria-hidden="true" />}
              title="No reviews yet"
              description="Guest reviews of your properties will show up here after their stay."
            />
          }
        >
          {(items) => (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Property</TableHead>
                  <TableHead>Rating</TableHead>
                  <TableHead>Review</TableHead>
                  <TableHead>Date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((item) => (
                  <TableRow key={item.id}>
                    <TableCell className="text-foreground">
                      {item.property_id ? (
                        <Link href={`/app/properties/${item.property_id}`} className="hover:underline">
                          {item.property_name ?? "—"}
                        </Link>
                      ) : (
                        item.property_name ?? "—"
                      )}
                    </TableCell>
                    <TableCell>
                      {item.overall_rating != null ? (
                        <span className="flex items-center gap-1 text-foreground">
                          <Star className="size-4 fill-amber-400 text-amber-400" aria-hidden="true" />
                          {item.overall_rating}
                        </span>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                    <TableCell className="max-w-md truncate text-muted-foreground">{item.raw_text}</TableCell>
                    <TableCell className="text-muted-foreground">{formatDate(item.created_at)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </DataState>
      </div>
    </div>
  );
}
