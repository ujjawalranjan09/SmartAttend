import * as React from "react";
import { cn } from "@/lib/utils";

interface PageHeaderProps {
  title: string;
  description?: React.ReactNode;
  actions?: React.ReactNode;
  eyebrow?: string;
  className?: string;
}

export function PageHeader({ title, description, actions, eyebrow, className }: PageHeaderProps) {
  return (
    <div className={cn("flex flex-wrap items-end justify-between gap-4 mb-6", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="text-xs font-semibold uppercase tracking-wider text-brand-500 mb-1">{eyebrow}</div>}
        <h1 className="text-2xl sm:text-3xl font-bold tracking-tight">{title}</h1>
        {description && <p className="text-[var(--muted-foreground)] mt-1 text-sm">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 flex-wrap">{actions}</div>}
    </div>
  );
}
