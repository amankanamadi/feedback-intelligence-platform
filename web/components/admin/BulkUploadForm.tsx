"use client";

import { useRef, useState } from "react";
import { Upload } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { useBulkUploadMutation } from "@/hooks/use-bulk-upload";
import { isApiError } from "@/lib/auth";

export function BulkUploadForm() {
  const [fileName, setFileName] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const bulkUploadMutation = useBulkUploadMutation();

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    setFileName(file?.name ?? null);
  };

  const handleUpload = () => {
    const file = inputRef.current?.files?.[0];
    if (!file) return;

    bulkUploadMutation.mutate(file, {
      onSuccess: (items) => {
        toast.success(`Uploaded and classified ${items.length} feedback item(s).`);
        setFileName(null);
        if (inputRef.current) inputRef.current.value = "";
      },
      onError: (error) => {
        toast.error(isApiError(error) ? error.message : "Bulk upload failed. Please try again.");
      },
    });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <label className="inline-flex cursor-pointer items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-muted">
        <Upload className="size-4" aria-hidden="true" />
        {fileName ?? "Choose CSV/JSON file"}
        <input ref={inputRef} type="file" accept=".csv,.json" className="hidden" onChange={handleFileChange} />
      </label>
      <Button size="sm" onClick={handleUpload} disabled={!fileName} isLoading={bulkUploadMutation.isPending}>
        Upload
      </Button>
    </div>
  );
}
