import { cn } from "@/lib/utils";

interface LogoProps {
  /** Controls the icon container size. */
  size?: "sm" | "md" | "lg";
  /** When true, renders the "SmartAttend" wordmark next to the icon. */
  withWordmark?: boolean;
  className?: string;
}

const sizeMap = {
  sm: "h-8 w-8",
  md: "h-9 w-9",
  lg: "h-10 w-10",
};

const svgSizeMap = {
  sm: 16,
  md: 20,
  lg: 22,
};

export function Logo({ size = "md", withWordmark = false, className }: LogoProps) {
  const s = svgSizeMap[size];

  return (
    <div className={cn("flex items-center gap-2.5 overflow-hidden", className)}>
      <div
        className={cn(
          "rounded-lg bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shrink-0 shadow-sm shadow-brand-500/30",
          sizeMap[size]
        )}
      >
        <svg width={s} height={s} viewBox="0 0 40 40" fill="none" aria-hidden="true">
          <path d="M10 20 L20 10 L30 20 L20 30 Z" stroke="white" strokeWidth="2.5" fill="none" strokeLinejoin="round" />
          <circle cx="20" cy="20" r="3.5" fill="white" />
        </svg>
      </div>
      {withWordmark && <span className="font-bold tracking-tight whitespace-nowrap">SmartAttend</span>}
    </div>
  );
}
