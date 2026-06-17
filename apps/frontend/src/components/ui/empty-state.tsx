import * as React from "react";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center text-center py-16 px-6 rounded-xl border border-dashed border-[var(--border)] bg-[var(--card)]/40 animate-[fadeIn_0.3s_ease-out]",
        className
      )}
    >
      {icon && (
        <div className="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-[var(--muted)] text-[var(--muted-foreground)]">
          {icon}
        </div>
      )}
      <h3 className="text-base font-semibold mb-1">{title}</h3>
      {description && (
        <p className="text-sm text-[var(--muted-foreground)] max-w-sm mb-4">{description}</p>
      )}
      {action}
    </div>
  );
}
