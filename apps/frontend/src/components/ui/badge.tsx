import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "bg-brand-500/15 text-brand-600 dark:text-brand-400 border border-brand-500/20",
        secondary: "bg-[var(--secondary)] text-[var(--secondary-foreground)] border border-[var(--border)]",
        success: "bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20",
        warning: "bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/20",
        destructive: "bg-red-500/15 text-red-600 dark:text-red-400 border border-red-500/20",
        outline: "border border-[var(--border)] text-[var(--foreground)]",
        muted: "bg-[var(--muted)] text-[var(--muted-foreground)] border border-transparent",
        info: "bg-blue-500/15 text-blue-600 dark:text-blue-400 border border-blue-500/20",
        proxy: "bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/20",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <span className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
