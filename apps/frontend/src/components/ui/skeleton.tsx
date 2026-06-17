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

export { Skeleton };
