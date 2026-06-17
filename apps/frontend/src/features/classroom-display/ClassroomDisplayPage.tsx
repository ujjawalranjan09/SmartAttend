import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Users, CheckCircle2, Clock, Wifi, WifiOff, Tv } from "lucide-react";
import { sessionsApi, getToken } from "@/lib/api";
import { formatTime } from "@/lib/utils";

interface AttendanceRecord {
  student_name?: string;
  roll_number?: string;
  status?: string;
  method?: string;
  marked_at?: string;
}

export function ClassroomDisplayPage() {
  const params = new URLSearchParams(window.location.search);
  const sessionId = params.get("session_id") || "";
  const tokenParam = params.get("token");

  // Persist token from query if present (so polling works)
  useEffect(() => {
    if (tokenParam) localStorage.setItem("smartattend_token", tokenParam);
  }, [tokenParam]);

  const { data, isError, isLoading } = useQuery({
    queryKey: ["session-attendance", sessionId],
    queryFn: async () => sessionsApi.attendance(sessionId),
    refetchInterval: 5_000,
    enabled: !!sessionId,
    retry: 1,
  });

  const session = (data as any)?.session || {};
  const records: AttendanceRecord[] = (data as any)?.records || [];
  const total = (data as any)?.total || (data as any)?.enrolled_count || 0;
  const present = records.filter((r) => r.status === "present").length;
  const pct = total > 0 ? Math.round((present / total) * 100) : 0;
  const [clock, setClock] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  if (!sessionId) {
    return (
      <div className="min-h-screen grid place-items-center bg-gradient-to-br from-neutral-950 via-neutral-900 to-neutral-950 text-white">
        <div className="text-center">
          <Tv className="h-16 w-16 mx-auto text-neutral-700 mb-4" />
          <h1 className="text-4xl font-bold mb-2">No session specified</h1>
          <p className="text-neutral-400">Open this page from a session's "Display" button.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-neutral-950 via-neutral-900 to-neutral-950 text-white flex flex-col p-8 overflow-hidden">
      {/* Header */}
      <div className="flex items-start justify-between mb-8 animate-[fadeIn_0.5s_ease-out]">
        <div>
          <div className="text-xs font-semibold uppercase tracking-widest text-brand-400 mb-2">Live attendance</div>
          <h1 className="text-5xl font-bold tracking-tight">{session.course_name || "Session"}</h1>
          <div className="text-xl text-neutral-400 mt-2">
            {session.faculty_name || ""} · {session.room || ""}
          </div>
        </div>
        <div className="text-right">
          <div className="text-6xl font-mono tabular-nums font-light">{clock.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}</div>
          <div className="text-sm text-neutral-400 mt-1">{clock.toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</div>
          <div className="flex items-center gap-1.5 justify-end mt-2 text-xs">
            {isError ? <><WifiOff className="h-3 w-3 text-red-500" /><span className="text-red-400">Reconnecting…</span></> : <><Wifi className="h-3 w-3 text-emerald-500 animate-pulse" /><span className="text-emerald-400">Live</span></>}
          </div>
        </div>
      </div>

      {/* Hero stats */}
      <div className="grid grid-cols-3 gap-6 mb-8">
        <StatCard icon={<CheckCircle2 className="h-8 w-8" />} label="Present" value={present} variant="emerald" delay="0ms" />
        <StatCard icon={<Users className="h-8 w-8" />} label="Enrolled" value={total} variant="brand" delay="100ms" />
        <div className="rounded-2xl border border-neutral-800 bg-neutral-900/60 backdrop-blur p-6 flex flex-col justify-between animate-[slideUp_0.5s_ease-out_200ms_both]" style={{ animationDelay: "200ms" }}>
          <div className="flex items-center gap-2 text-neutral-400">
            <Clock className="h-5 w-5" />
            <span className="text-sm uppercase tracking-wider font-semibold">Attendance</span>
          </div>
          <div className="text-7xl font-bold tabular-nums">
            <span className={pct >= 75 ? "text-emerald-400" : pct >= 50 ? "text-amber-400" : "text-red-400"}>{pct}</span>
            <span className="text-3xl text-neutral-500">%</span>
          </div>
          <div className="h-2 rounded-full bg-neutral-800 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all duration-700 ease-out ${pct >= 75 ? "bg-gradient-to-r from-emerald-400 to-emerald-500" : pct >= 50 ? "bg-gradient-to-r from-amber-400 to-amber-500" : "bg-gradient-to-r from-red-400 to-red-500"}`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>
      </div>

      {/* Feed */}
      <div className="flex-1 rounded-2xl border border-neutral-800 bg-neutral-900/40 backdrop-blur p-6 overflow-hidden flex flex-col">
        <div className="text-sm uppercase tracking-wider font-semibold text-neutral-400 mb-4 flex items-center gap-2">
          <span className="relative flex h-2 w-2">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
            <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500" />
          </span>
          Live attendance feed
        </div>
        <div className="flex-1 overflow-y-auto space-y-1">
          {isLoading && <div className="text-center py-12 text-neutral-500">Loading…</div>}
          {!isLoading && records.length === 0 && (
            <div className="text-center py-12 text-neutral-500">
              <Users className="h-12 w-12 mx-auto mb-3 text-neutral-700" />
              <p>Waiting for the first attendance event…</p>
            </div>
          )}
          {records.slice(-15).reverse().map((r, i) => (
            <div
              key={`${r.roll_number || r.student_name}-${r.marked_at}-${i}`}
              className="flex items-center gap-4 p-3 rounded-lg bg-neutral-900/60 border border-neutral-800/60 animate-[slideInRight_0.3s_ease-out]"
              style={{ animationDelay: `${i * 30}ms` }}
            >
              <div className={`h-10 w-10 rounded-full flex items-center justify-center shrink-0 ${r.status === "present" ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                {r.status === "present" ? <CheckCircle2 className="h-5 w-5" /> : <span className="text-xs font-bold">✕</span>}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-semibold text-lg truncate">{r.student_name || "Student"}</div>
                <div className="text-sm text-neutral-500">{r.roll_number || ""}</div>
              </div>
              <div className="text-sm text-neutral-400 tabular-nums">
                {r.marked_at ? formatTime(r.marked_at) : ""}
              </div>
              <Badge variant={r.method === "face" ? "info" : "muted"} className="text-xs">{r.method || "qr"}</Badge>
            </div>
          ))}
        </div>
      </div>

      {/* Footer watermark */}
      <div className="mt-6 flex items-center justify-between text-xs text-neutral-500">
        <div className="flex items-center gap-2">
          <div className="h-6 w-6 rounded bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center">
            <svg width="14" height="14" viewBox="0 0 40 40" fill="none">
              <path d="M10 20 L20 10 L30 20 L20 30 Z" stroke="white" strokeWidth="3" fill="none" strokeLinejoin="round"/>
              <circle cx="20" cy="20" r="3" fill="white"/>
            </svg>
          </div>
          <span>SmartAttend Classroom Display</span>
        </div>
        <div>Session: {sessionId.slice(0, 8)}…</div>
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, variant, delay }: { icon: React.ReactNode; label: string; value: number; variant: "emerald" | "brand"; delay: string }) {
  const colorMap = {
    emerald: "from-emerald-500/20 to-emerald-500/0 text-emerald-400",
    brand: "from-brand-500/20 to-brand-500/0 text-brand-400",
  };
  return (
    <div
      className="rounded-2xl border border-neutral-800 bg-neutral-900/60 backdrop-blur p-6 flex flex-col justify-between relative overflow-hidden animate-[slideUp_0.5s_ease-out_both]"
      style={{ animationDelay: delay }}
    >
      <div className={`absolute inset-0 bg-gradient-to-br ${colorMap[variant]} opacity-50`} />
      <div className="relative flex items-center gap-2 text-neutral-400">
        {icon}
        <span className="text-sm uppercase tracking-wider font-semibold">{label}</span>
      </div>
      <div className="relative text-7xl font-bold tabular-nums">{value}</div>
    </div>
  );
}

function Badge({ children, variant, className }: { children: React.ReactNode; variant: "info" | "muted"; className?: string }) {
  const styles = variant === "info" ? "bg-blue-500/15 text-blue-400 border-blue-500/30" : "bg-neutral-800 text-neutral-400 border-neutral-700";
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium border ${styles} ${className || ""}`}>{children}</span>;
}
