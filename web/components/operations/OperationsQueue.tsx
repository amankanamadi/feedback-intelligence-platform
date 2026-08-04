"use client";

import { useState } from "react";
import Link from "next/link";
import { Inbox } from "lucide-react";
import { DataState } from "@/components/shared/DataState";
import { EmptyState } from "@/components/shared/EmptyState";
import { TableSkeleton } from "@/components/shared/LoadingSkeletons";
import { PriorityBadge, StatusBadge } from "@/components/shared/StatusBadge";
import { Badge } from "@/components/ui/badge";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { useFeedbackList } from "@/hooks/use-feedback-list";
import { formatDate } from "@/lib/format";
import {
  PRIORITY_OPTIONS,
  RESPONSIBLE_TEAM_OPTIONS,
  STATUS_OPTIONS,
  type FeedbackAdmin,
  type FeedbackListFilters,
  type FeedbackStatus,
  type Priority,
  type ResponsibleTeam,
} from "@/types/feedback";

type SelectFilterValue<T extends string> = T | "";

function FilterSelect<T extends string>({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: SelectFilterValue<T>;
  onChange: (value: SelectFilterValue<T>) => void;
  options: T[];
}) {
  return (
    <select
      aria-label={label}
      value={value}
      onChange={(e) => onChange(e.target.value as SelectFilterValue<T>)}
      className="h-10 rounded-md border border-border bg-card px-3 text-sm text-foreground"
    >
      <option value="">{label}</option>
      {options.map((option) => (
        <option key={option} value={option}>
          {option}
        </option>
      ))}
    </select>
  );
}

// Shared by the Operations queue (all responsible teams, adjustable) and
// the Trust & Safety queue (lockedResponsibleTeam fixes it to "Trust &
// Safety" and hides the selector).
export function OperationsQueue({
  lockedResponsibleTeam,
  defaultUnresolved = true,
}: {
  lockedResponsibleTeam?: ResponsibleTeam;
  defaultUnresolved?: boolean;
}) {
  const [priority, setPriority] = useState<SelectFilterValue<Priority>>("");
  const [status, setStatus] = useState<SelectFilterValue<FeedbackStatus>>("");
  const [responsibleTeam, setResponsibleTeam] = useState<SelectFilterValue<ResponsibleTeam>>("");
  const [escalatedOnly, setEscalatedOnly] = useState(false);
  const [slaBreachedOnly, setSlaBreachedOnly] = useState(false);
  const [unresolvedOnly, setUnresolvedOnly] = useState(defaultUnresolved);
  const [duplicatesOnly, setDuplicatesOnly] = useState(false);

  const filters: FeedbackListFilters = {
    limit: 200,
    priority: priority || undefined,
    status: status || undefined,
    responsible_team: lockedResponsibleTeam ?? (responsibleTeam || undefined),
    escalated: escalatedOnly || undefined,
    sla_breached: slaBreachedOnly || undefined,
    unresolved: unresolvedOnly || undefined,
    has_duplicates: duplicatesOnly || undefined,
  };
  const query = useFeedbackList(filters);

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-3">
        <FilterSelect label="All priorities" value={priority} onChange={setPriority} options={PRIORITY_OPTIONS} />
        <FilterSelect label="All statuses" value={status} onChange={setStatus} options={STATUS_OPTIONS} />
        {!lockedResponsibleTeam && (
          <FilterSelect
            label="All teams"
            value={responsibleTeam}
            onChange={setResponsibleTeam}
            options={RESPONSIBLE_TEAM_OPTIONS}
          />
        )}
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={unresolvedOnly} onChange={(e) => setUnresolvedOnly(e.target.checked)} />
          Unresolved only
        </label>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={escalatedOnly} onChange={(e) => setEscalatedOnly(e.target.checked)} />
          Escalated
        </label>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={slaBreachedOnly} onChange={(e) => setSlaBreachedOnly(e.target.checked)} />
          SLA breached
        </label>
        <label className="flex items-center gap-2 text-sm text-foreground">
          <input type="checkbox" checked={duplicatesOnly} onChange={(e) => setDuplicatesOnly(e.target.checked)} />
          Repeated
        </label>
      </div>

      <DataState
        query={query}
        skeleton={<TableSkeleton />}
        empty={(items) => items.length === 0}
        emptyState={
          <EmptyState
            icon={<Inbox className="size-10" aria-hidden="true" />}
            title="Nothing matches these filters"
            description="Try adjusting or clearing the filters above."
          />
        }
      >
        {(items) => (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Feedback</TableHead>
                <TableHead>Team</TableHead>
                <TableHead>Priority</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Flags</TableHead>
                <TableHead>Created</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(items as FeedbackAdmin[]).map((item) => (
                <TableRow key={item.id}>
                  <TableCell className="max-w-xs">
                    <Link href={`/app/feedback/${item.id}`} className="line-clamp-2 text-foreground hover:underline">
                      {item.raw_text}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{item.responsible_team ?? "-"}</TableCell>
                  <TableCell>{item.priority ? <PriorityBadge priority={item.priority} /> : "-"}</TableCell>
                  <TableCell>
                    <StatusBadge status={item.status} />
                  </TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {item.escalated && <Badge variant="destructive">Escalated</Badge>}
                      {item.sla_breached && <Badge variant="destructive">SLA</Badge>}
                      {item.duplicate_of_feedback_id && <Badge variant="muted">Dup</Badge>}
                    </div>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{formatDate(item.created_at)}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </DataState>
    </div>
  );
}
