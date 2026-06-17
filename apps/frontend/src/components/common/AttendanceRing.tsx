import { cn } from "@/lib/utils";
import { attendanceClass } from "@/lib/utils";

interface AttendanceRingProps {
  value: number; // 0-100
  size?: number;
  strokeWidth?: number;
  label?: string;
  className?: string;
}

export function AttendanceRing({ value, size = 120, strokeWidth = 10, label, className }: AttendanceRingProps) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const clamped = Math.max(0, Math.min(100, value));
  const offset = circumference - (clamped / 100) * circumference;
  const cls = attendanceClass(clamped);
  const color = cls === "success" ? "#10b981" : cls === "warning" ? "#f59e0b" : "#ef4444";

  return (
    <div className={cn("relative inline-flex items-center justify-center", className)} style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle cx={size/2} cy={size/2} r={radius} fill="none" stroke="var(--muted)" strokeWidth={strokeWidth} />
        <circle
          cx={size/2}
          cy={size/2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className="transition-[stroke-dashoffset] duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="text-2xl font-bold tabular-nums" style={{ color }}>{Math.round(clamped)}%</div>
        {label && <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mt-0.5">{label}</div>}
      </div>
    </div>
  );
}
