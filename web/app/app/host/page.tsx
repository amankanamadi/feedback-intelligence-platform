"use client";

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
import { Home, Inbox } from "lucide-react";

export default function HostDashboardPage() {
  const propertiesQuery = useHostProperties();
  const performanceQuery = useHostPerformance();
  const queueQuery = useHostQueue();

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
        <h2 className="mb-3 text-lg font-semibold text-foreground">Complaint queue</h2>
        <DataState
          query={queueQuery}
          skeleton={<TableSkeleton rows={4} />}
          empty={(data) => data.length === 0}
          emptyState={
            <EmptyState
              icon={<Inbox className="size-10" aria-hidden="true" />}
              title="Nothing routed to you right now"
              description="Complaints assigned to your properties will show up here."
            />
          }
        >
          {(items) => (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Feedback</TableHead>
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
    </div>
  );
}
