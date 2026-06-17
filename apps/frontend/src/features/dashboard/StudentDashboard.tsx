import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { CalendarCheck, CalendarX, Percent, Shield, Sparkles, ScanLine, Calendar, Target, BookOpen, ChevronRight } from "lucide-react";
import { Link } from "react-router-dom";
import { analyticsApi, dailyPlanApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { greeting, formatPercent } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { KpiCard } from "@/components/common/KpiCard";
import { AttendanceRing } from "@/components/common/AttendanceRing";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";

export function StudentDashboard() {
  const { user } = useAuth();
  const { data: analytics, isLoading } = useQuery({
    queryKey: ["analytics", "student", user?.id],
    queryFn: () => analyticsApi.student(user?.id),
  });
  const { data: routine } = useQuery({
    queryKey: ["routine", "today"],
    queryFn: () => dailyPlanApi.getRoutine(new Date().toISOString().split("T")[0]),
    retry: 0,
  });

  const pct = analytics?.overall_percentage ?? 0;
  const attended = analytics?.attended_classes ?? 0;
  const missed = analytics?.missed_classes ?? 0;
  const canMiss = analytics?.can_miss_more ?? 0;
  const greet = greeting();
  const weeklyTrend = analytics?.weekly_trend || [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${greet.emoji} ${greet.text}`}
        title={`Hi, ${user?.full_name?.split(" ")[0] || "there"} 👋`}
        description={new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        actions={
          <>
            <Button asChild variant="outline"><Link to="/qr-scanner"><ScanLine /> Scan QR</Link></Button>
            <Button asChild variant="gradient"><Link to="/daily-plan"><CalendarClock /> My Day</Link></Button>
          </>
        }
      />

      {analytics?.at_risk_alert && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 flex items-start gap-3 animate-[slideUp_0.3s_ease-out]">
          <div className="h-9 w-9 rounded-full bg-red-500/20 flex items-center justify-center shrink-0">
            <Sparkles className="h-4 w-4 text-red-500" />
          </div>
          <div className="flex-1">
            <div className="font-semibold text-red-600 dark:text-red-400">You're at {pct}% — below the 75% threshold</div>
            <div className="text-sm text-red-600/80 dark:text-red-400/80 mt-0.5">
              Attend <strong>{analytics?.classes_needed ?? "?"} more classes</strong> to recover safe status.
            </div>
          </div>
          <Button asChild size="sm" variant="outline"><Link to="/attendance">View details</Link></Button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Overall attendance"
          value={isLoading ? "—" : formatPercent(pct)}
          icon={Percent}
          variant={pct >= 75 ? "success" : pct >= 60 ? "warning" : "error"}
          delta={pct >= 75 ? { value: "On track", direction: "up" } : { value: "Below threshold", direction: "down" }}
        />
        <KpiCard label="Classes attended" value={isLoading ? "—" : attended} icon={CalendarCheck} variant="success" />
        <KpiCard label="Classes missed" value={isLoading ? "—" : missed} icon={CalendarX} variant="warning" />
        <KpiCard label="Can still miss" value={isLoading ? "—" : canMiss} icon={Shield} variant={canMiss > 0 ? "brand" : "error"} description="Classes before crossing 75% threshold" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Trend chart */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Attendance trend</CardTitle>
                <CardDescription>Your last 8 weeks</CardDescription>
              </div>
              <Badge variant="success">+5%</Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {weeklyTrend.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weeklyTrend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trendGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey={(d: any) => d.label || d.week} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip
                      contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }}
                      labelStyle={{ color: "var(--foreground)" }}
                      formatter={(v: number) => [`${v}%`, "Attendance"]}
                    />
                    <Area type="monotone" dataKey="pct" stroke="#14b8a6" strokeWidth={2.5} fill="url(#trendGrad)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <Skeleton className="h-full w-full" />
              )}
            </div>
          </CardContent>
        </Card>

        {/* Ring */}
        <Card>
          <CardHeader>
            <CardTitle>Your status</CardTitle>
            <CardDescription>Real-time summary</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col items-center gap-4 pt-2">
            <AttendanceRing value={pct} size={160} strokeWidth={14} label="Overall" />
            <div className="text-center">
              <div className="text-sm font-medium">{pct >= 75 ? "Safe zone" : pct >= 60 ? "At risk" : "Shortage"}</div>
              <div className="text-xs text-[var(--muted-foreground)] mt-1">
                {pct >= 75 ? "Keep it up — you're above the 75% line." : "Pull up your attendance to stay safe."}
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Course breakdown */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Course breakdown</CardTitle>
                <CardDescription>Attendance per enrolled course</CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {analytics?.by_course?.length ? analytics.by_course.map((c: any) => {
              const color = c.percentage >= 75 ? "[&>div]:bg-emerald-500" : c.percentage >= 60 ? "[&>div]:bg-amber-500" : "[&>div]:bg-red-500";
              return (
                <div key={c.course_name}>
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-sm font-medium truncate">{c.course_name}</span>
                    <span className="text-sm font-semibold tabular-nums">{c.percentage}%</span>
                  </div>
                  <Progress value={c.percentage} className={color} />
                </div>
              );
            }) : (
              <p className="text-sm text-[var(--muted-foreground)] py-6 text-center">No course data yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Today's routine */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Today's routine</CardTitle>
                <CardDescription className="capitalize">
                  {routine?.generated_by === "llm" ? "AI-generated plan" : routine?.generated_by === "cached" ? "Cached plan" : "Basic plan"}
                </CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm"><Link to="/daily-plan">View all <ChevronRight className="h-3 w-3" /></Link></Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-1.5">
            {routine?.routine?.slice(0, 5).map((item: any, i: number) => {
              const colors: Record<string, string> = { class: "bg-brand-500", study: "bg-emerald-500", break: "bg-amber-500", free: "bg-neutral-400" };
              const dot = colors[item.type] || "bg-neutral-400";
              return (
                <div key={i} className="flex items-center gap-3 py-1.5">
                  <div className={`h-7 w-1 rounded-full ${dot}`} />
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{item.course_name || item.title || item.type}</div>
                    <div className="text-xs text-[var(--muted-foreground)] tabular-nums">{item.start} – {item.end}</div>
                  </div>
                  <Badge variant="muted" className="capitalize text-[10px]">{item.type}</Badge>
                </div>
              );
            })}
            {!routine?.routine?.length && (
              <div className="text-center py-6">
                <p className="text-sm text-[var(--muted-foreground)]">No routine for today.</p>
                <Button asChild size="sm" variant="outline" className="mt-2"><Link to="/daily-plan"><Calendar className="h-3 w-3" /> Set up your day</Link></Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Quick actions */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {[
          { to: "/qr-scanner", icon: ScanLine, label: "Mark attendance", desc: "Scan session QR", color: "from-brand-500 to-brand-700" },
          { to: "/daily-plan", icon: Calendar, label: "My day", desc: "Plan & suggestions", color: "from-blue-500 to-indigo-600" },
          { to: "/profile", icon: Target, label: "Goals", desc: "Track progress", color: "from-emerald-500 to-teal-600" },
          { to: "/sessions", icon: BookOpen, label: "Schedule", desc: "All classes", color: "from-amber-500 to-orange-600" },
        ].map(({ to, icon: Icon, label, desc, color }) => (
          <Link key={to} to={to} className="group relative overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:border-transparent hover:shadow-[var(--shadow-elevated)]">
            <div className={`absolute inset-0 bg-gradient-to-br ${color} opacity-0 group-hover:opacity-100 transition-opacity`} />
            <div className="relative">
              <div className="h-9 w-9 rounded-lg bg-[var(--muted)] group-hover:bg-white/20 flex items-center justify-center mb-3 transition-colors">
                <Icon className="h-4 w-4 group-hover:text-white transition-colors" />
              </div>
              <div className="text-sm font-semibold group-hover:text-white transition-colors">{label}</div>
              <div className="text-xs text-[var(--muted-foreground)] group-hover:text-white/70 transition-colors">{desc}</div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

// Convenience icon for the action button
function CalendarClock(props: any) {
  return <Calendar {...props} />;
}
