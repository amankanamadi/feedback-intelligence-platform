import { Download } from "lucide-react";
import { Button } from "@/components/ui/button";
import { API_BASE_URL } from "@/lib/api-client";
import type { FeedbackListFilters } from "@/types/feedback";

function buildExportQuery(filters: FeedbackListFilters): string {
  const params = new URLSearchParams();
  if (filters.main_category) params.set("main_category", filters.main_category);
  if (filters.sentiment) params.set("sentiment", filters.sentiment);
  if (filters.search) params.set("search", filters.search);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function ExportButtons({ filters }: { filters: FeedbackListFilters }) {
  const query = buildExportQuery(filters);

  return (
    <div className="flex gap-2">
      <Button variant="outline" size="sm" asChild>
        {/* Plain top-level navigation, not a fetch() call - the browser
            attaches the session cookie automatically, same as any other
            same-site GET, and streams the file back directly. */}
        <a href={`${API_BASE_URL}/feedback/export/csv${query}`}>
          <Download className="size-4" aria-hidden="true" />
          Export CSV
        </a>
      </Button>
      <Button variant="outline" size="sm" asChild>
        <a href={`${API_BASE_URL}/feedback/export/pdf${query}`}>
          <Download className="size-4" aria-hidden="true" />
          Export PDF
        </a>
      </Button>
    </div>
  );
}
