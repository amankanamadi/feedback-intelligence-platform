import type { ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { ErrorState } from "@/components/shared/ErrorState";
import { isApiError } from "@/lib/auth";

type DataStateProps<T> = {
  query: UseQueryResult<T>;
  skeleton: ReactNode;
  empty?: (data: T) => boolean;
  emptyState?: ReactNode;
  children: (data: T) => ReactNode;
};

export function DataState<T>({ query, skeleton, empty, emptyState, children }: DataStateProps<T>) {
  if (query.isPending) return <>{skeleton}</>;

  if (query.isError) {
    const message = isApiError(query.error) ? query.error.message : "Please try again.";
    return <ErrorState message={message} onRetry={() => query.refetch()} />;
  }

  if (empty?.(query.data) && emptyState) return <>{emptyState}</>;

  return <>{children(query.data)}</>;
}
