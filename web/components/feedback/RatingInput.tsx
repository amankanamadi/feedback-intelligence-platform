"use client";

import { cn } from "@/lib/utils";

export function RatingInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | null;
  onChange: (value: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <span className="text-sm font-medium text-foreground">{label}</span>
      <div className="flex gap-1.5" role="radiogroup" aria-label={label}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            onClick={() => onChange(n)}
            className={cn(
              "flex size-9 items-center justify-center rounded-md border border-border text-sm font-medium transition-colors",
              value === n ? "bg-primary text-primary-foreground" : "bg-card text-foreground hover:bg-muted"
            )}
          >
            {n}
          </button>
        ))}
      </div>
    </div>
  );
}
