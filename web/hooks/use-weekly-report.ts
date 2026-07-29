import { useMutation } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api-client";
import type { WeeklyReportResponse } from "@/types/analytics";

// A mutation, not a query - this triggers a real LLM call on the backend,
// so it must only run on an explicit "Generate Report" click, never
// automatically on page load or a background refetch.
export function useWeeklyReportMutation() {
  return useMutation({
    mutationFn: () => apiFetch<WeeklyReportResponse>("/reports/weekly"),
  });
}
