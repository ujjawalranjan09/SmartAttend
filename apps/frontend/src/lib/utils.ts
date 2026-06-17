import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function initials(name?: string | null): string {
  if (!name) return "U";
  return name
    .split(" ")
    .map((n) => n[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

export function formatDate(d: string | Date | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatDateTime(d: string | Date | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleString("en-IN", {
    day: "numeric",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatTime(d: string | Date | null | undefined): string {
  if (!d) return "—";
  return new Date(d).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatPercent(n: number | null | undefined): string {
  if (n == null || isNaN(n)) return "—";
  return `${Math.round(n)}%`;
}

export function attendanceClass(pct: number): "success" | "warning" | "error" {
  if (pct >= 75) return "success";
  if (pct >= 60) return "warning";
  return "error";
}

export function greeting(): { text: string; emoji: string } {
  const h = new Date().getHours();
  if (h < 12) return { text: "Good morning", emoji: "🌅" };
  if (h < 17) return { text: "Good afternoon", emoji: "☀️" };
  return { text: "Good evening", emoji: "🌆" };
}
