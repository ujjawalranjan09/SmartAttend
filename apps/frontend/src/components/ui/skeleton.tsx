import { cn } from "@/lib/utils";

function Skeleton({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "animate-pulse rounded-md bg-gradient-to-r from-[var(--muted)] via-[var(--border)] to-[var(--muted)] bg-[length:200%_100%] animate-[shimmer_2s_infinite]",
        className
      )}
      {...props}
    />
  );
}

/** Multi-line text placeholder. `lines` controls row count; last line is shorter. */
function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
  return (
    <div className={cn("flex flex-col gap-2", className)} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton key={i} className={cn("h-3", i === lines - 1 ? "w-2/3" : "w-full")} />
      ))}
    </div>
  );
}

/** Card-shaped placeholder mimicking a Card with header + body. */
function SkeletonCard({ className }: { className?: string }) {
  return (
    <div
      className={cn("rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-sm", className)}
      aria-hidden="true"
    >
      <Skeleton className="mb-3 h-4 w-1/3" />
      <Skeleton className="mb-2 h-6 w-2/3" />
      <SkeletonText lines={2} className="mt-4" />
    </div>
  );
}

export { Skeleton, SkeletonText, SkeletonCard };
