import * as React from "react";
import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown, Minus, type LucideIcon } from "lucide-react";

interface KpiCardProps {
  label: string;
  value: React.ReactNode;
  icon?: LucideIcon;
  variant?: "brand" | "success" | "warning" | "error" | "info" | "neutral";
  delta?: { value: string; direction: "up" | "down" | "flat" };
  description?: string;
  className?: string;
}

const variantStyles = {
  brand:   { iconBg: "bg-brand-500/15 text-brand-500",         bar: "from-brand-400 to-brand-600" },
  success: { iconBg: "bg-emerald-500/15 text-emerald-500",     bar: "from-emerald-400 to-emerald-600" },
  warning: { iconBg: "bg-amber-500/15 text-amber-500",         bar: "from-amber-400 to-amber-600" },
  error:   { iconBg: "bg-red-500/15 text-red-500",             bar: "from-red-400 to-red-600" },
  info:    { iconBg: "bg-blue-500/15 text-blue-500",           bar: "from-blue-400 to-blue-600" },
  neutral: { iconBg: "bg-[var(--muted)] text-[var(--muted-foreground)]", bar: "from-neutral-400 to-neutral-600" },
};

export function KpiCard({ label, value, icon: Icon, variant = "brand", delta, description, className }: KpiCardProps) {
  const v = variantStyles[variant];
  return (
    <div className={cn(
      "group relative overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-5 transition-all hover:shadow-[var(--shadow-soft)] hover:border-brand-500/30",
      className
    )}>
      <div className={cn("absolute inset-x-0 top-0 h-0.5 bg-gradient-to-r opacity-0 group-hover:opacity-100 transition-opacity", v.bar)} />
      <div className="flex items-start justify-between gap-3 mb-3">
        {Icon && (
          <div className={cn("flex h-10 w-10 items-center justify-center rounded-lg shrink-0", v.iconBg)}>
            <Icon className="h-5 w-5" />
          </div>
        )}
        {delta && (
          <div className={cn(
            "flex items-center gap-1 text-xs font-semibold rounded-full px-2 py-0.5",
            delta.direction === "up" && "text-emerald-600 bg-emerald-500/10",
            delta.direction === "down" && "text-red-600 bg-red-500/10",
            delta.direction === "flat" && "text-[var(--muted-foreground)] bg-[var(--muted)]"
          )}>
            {delta.direction === "up" && <TrendingUp className="h-3 w-3" />}
            {delta.direction === "down" && <TrendingDown className="h-3 w-3" />}
            {delta.direction === "flat" && <Minus className="h-3 w-3" />}
            {delta.value}
          </div>
        )}
      </div>
      <div className="text-2xl font-bold tracking-tight font-variant-numeric tabular-nums">{value}</div>
      <div className="text-sm text-[var(--muted-foreground)] mt-0.5">{label}</div>
      {description && <div className="text-xs text-[var(--muted-foreground)] mt-2 opacity-70">{description}</div>}
    </div>
  );
}
