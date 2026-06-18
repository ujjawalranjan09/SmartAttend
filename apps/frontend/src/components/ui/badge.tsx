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
        success: "bg-[var(--success)]/15 text-[var(--success)] border border-[var(--success)]/20",
        warning: "bg-[var(--warning)]/15 text-[var(--warning)] border border-[var(--warning)]/20",
        destructive: "bg-[var(--error)]/15 text-[var(--error)] border border-[var(--error)]/20",
        outline: "border border-[var(--border)] text-[var(--foreground)]",
        muted: "bg-[var(--muted)] text-[var(--muted-foreground)] border border-transparent",
        info: "bg-[var(--info)]/15 text-[var(--info)] border border-[var(--info)]/20",
        proxy: "bg-purple-500/15 text-purple-600 dark:text-purple-400 border border-purple-500/20",
      },
    },
    defaultVariants: { variant: "default" },
  }
);

// Per-variant dot colors for the leading status dot.
const dotColor: Record<string, string> = {
  default: "bg-brand-500",
  success: "bg-[var(--success)]",
  warning: "bg-[var(--warning)]",
  destructive: "bg-[var(--error)]",
  info: "bg-[var(--info)]",
  proxy: "bg-purple-500",
  secondary: "bg-[var(--muted-foreground)]",
  outline: "bg-[var(--muted-foreground)]",
  muted: "bg-[var(--muted-foreground)]",
};

export interface BadgeProps
  extends React.HTMLAttributes<HTMLSpanElement>,
    VariantProps<typeof badgeVariants> {
  /** Show a leading pulsing status dot. */
  dot?: boolean;
}

function Badge({ className, variant = "default", dot, children, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props}>
      {dot && (
        <span className={cn("relative flex size-1.5", !children && "sr-only")}>
          <span
            className={cn(
              "absolute inline-flex h-full w-full animate-ping rounded-full opacity-75",
              dotColor[variant ?? "default"]
            )}
          />
          <span className={cn("relative inline-flex size-1.5 rounded-full", dotColor[variant ?? "default"])} />
        </span>
      )}
      {children}
    </span>
  );
}

export { Badge, badgeVariants };
