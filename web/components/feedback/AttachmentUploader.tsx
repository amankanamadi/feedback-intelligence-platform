"use client";

import { Paperclip, X } from "lucide-react";
import { Button } from "@/components/ui/button";

const ACCEPTED_EXTENSIONS = ".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.log,.csv";
const MAX_FILES = 5;

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function AttachmentUploader({
  files,
  onChange,
}: {
  files: File[];
  onChange: (files: File[]) => void;
}) {
  const handlePick = (e: React.ChangeEvent<HTMLInputElement>) => {
    const picked = Array.from(e.target.files ?? []);
    onChange([...files, ...picked].slice(0, MAX_FILES));
    e.target.value = "";
  };

  const removeAt = (index: number) => {
    onChange(files.filter((_, i) => i !== index));
  };

  return (
    <div className="flex flex-col gap-2">
      <label className="inline-flex w-fit cursor-pointer items-center gap-2 rounded-md border border-border bg-card px-3 py-2 text-sm font-medium text-foreground hover:bg-muted">
        <Paperclip className="size-4" aria-hidden="true" />
        Attach files
        <input
          type="file"
          multiple
          accept={ACCEPTED_EXTENSIONS}
          className="hidden"
          onChange={handlePick}
          disabled={files.length >= MAX_FILES}
        />
      </label>
      {files.length > 0 && (
        <ul className="flex flex-col gap-1">
          {files.map((file, index) => (
            <li key={`${file.name}-${index}`} className="flex items-center justify-between rounded-md bg-muted px-3 py-2 text-sm">
              <span className="truncate text-foreground">
                {file.name} <span className="text-muted-foreground">({formatFileSize(file.size)})</span>
              </span>
              <Button type="button" variant="ghost" size="sm" onClick={() => removeAt(index)} aria-label={`Remove ${file.name}`}>
                <X className="size-4" />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <p className="text-xs text-muted-foreground">Up to {MAX_FILES} files. Images, PDFs, text, and CSV files are supported.</p>
    </div>
  );
}
