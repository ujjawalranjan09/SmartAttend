import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Calendar, Users, AlertCircle, Play, Plus, ChevronRight, Activity, TrendingUp, BellRing } from "lucide-react";
import { sessionsApi, alertsApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { greeting, formatDateTime, attendanceClass } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { KpiCard } from "@/components/common/KpiCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

const statusVariant: Record<string, any> = { active: "success", scheduled: "default", completed: "muted", cancelled: "destructive", ended: "muted" };

export function FacultyDashboard() {
  const { user } = useAuth();
  const greet = greeting();

  const { data: sessions = [], isLoading: l1 } = useQuery({
    queryKey: ["sessions", "recent"],
    queryFn: async () => {
      const res = await sessionsApi.list({ limit: 8 });
      return (res as any)?.items || (res as any) || [];
    },
  });

  const { data: alerts = [] } = useQuery({
    queryKey: ["alerts", "unresolved"],
    queryFn: async () => {
      try {
        const res = await alertsApi.list({ limit: 8, is_resolved: false });
        return (res as any)?.items || (res as any) || [];
      } catch { return []; }
    },
  });

  const activeCount = sessions.filter((s: any) => s.status === "active").length;
  const totalAtt = sessions.reduce((acc: number, s: any) => acc + (s.present_count || s.attendance_count || 0), 0);
  const totalEnr = sessions.reduce((acc: number, s: any) => acc + (s.total_enrolled || s.enrolled_count || 0), 0);
  const avgRate = totalEnr > 0 ? Math.round((totalAtt / totalEnr) * 100) : 0;

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${greet.emoji} ${greet.text}, Prof.`}
        title={`Welcome back, ${user?.full_name?.split(" ")[0] || "Faculty"} 👨‍🏫`}
        description={new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        actions={
          <Button asChild variant="gradient"><Link to="/sessions"><Plus /> New session</Link></Button>
        }
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard label="Sessions this week" value={l1 ? "—" : sessions.length} icon={Calendar} variant="brand" />
        <KpiCard label="Active now" value={activeCount} icon={Activity} variant={activeCount > 0 ? "success" : "neutral"} description={activeCount > 0 ? "Sessions currently live" : "No live sessions"} />
        <KpiCard label="Avg attendance rate" value={`${avgRate}%`} icon={TrendingUp} variant={avgRate >= 75 ? "success" : avgRate >= 60 ? "warning" : "error"} delta={{ value: avgRate >= 75 ? "Healthy" : "Needs push", direction: avgRate >= 75 ? "up" : "down" }} />
        <KpiCard label="Unresolved alerts" value={alerts.length} icon={BellRing} variant={alerts.length > 0 ? "error" : "success"} description={alerts.length > 0 ? "Action needed" : "All clear"} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Recent sessions</CardTitle>
                <CardDescription>Latest classes you've conducted</CardDescription>
              </div>
              <Button asChild variant="ghost" size="sm"><Link to="/sessions">View all <ChevronRight className="h-3 w-3" /></Link></Button>
            </div>
          </CardHeader>
          <CardContent>
            {l1 ? (
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14 w-full" />)}
              </div>
            ) : sessions.length === 0 ? (
              <div className="text-center py-10">
                <Calendar className="h-10 w-10 mx-auto text-[var(--muted-foreground)] mb-3" />
                <p className="text-sm text-[var(--muted-foreground)]">No sessions yet. Create your first one.</p>
                <Button asChild size="sm" variant="outline" className="mt-3"><Link to="/sessions"><Plus /> Start session</Link></Button>
              </div>
            ) : (
              <div className="space-y-2">
                {sessions.map((s: any) => {
                  const present = s.present_count ?? s.attendance_count ?? 0;
                  const enrolled = s.total_enrolled ?? s.enrolled_count ?? 0;
                  const pct = enrolled ? Math.round((present / enrolled) * 100) : 0;
                  return (
                    <div key={s.id} className="flex items-center gap-3 p-3 rounded-lg hover:bg-[var(--accent)] transition-colors">
                      <div className="h-10 w-10 rounded-lg bg-brand-500/10 text-brand-500 flex items-center justify-center shrink-0">
                        <Calendar className="h-4 w-4" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{s.course_name || s.course_id || "Session"}</div>
                        <div className="text-xs text-[var(--muted-foreground)]">{formatDateTime(s.start_time || s.started_at || s.created_at)}</div>
                      </div>
                      <div className="text-right shrink-0">
                        <div className="text-sm font-semibold tabular-nums">{present}/{enrolled}</div>
                        <div className="text-[10px] text-[var(--muted-foreground)]">{pct}% present</div>
                      </div>
                      <Badge variant={statusVariant[s.status] || "muted"} className="capitalize">{s.status || "unknown"}</Badge>
                      {s.status === "active" && (
                        <Button asChild size="sm" variant="outline"><Link to={`/live-session/${s.id}`}><Play className="h-3 w-3" /> Live</Link></Button>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Alerts feed</CardTitle>
                <CardDescription>Proxy and anomaly signals</CardDescription>
              </div>
              {alerts.length > 0 && <Badge variant="destructive">{alerts.length}</Badge>}
            </div>
          </CardHeader>
          <CardContent className="space-y-2">
            {alerts.length === 0 ? (
              <div className="text-center py-8">
                <div className="h-10 w-10 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto mb-2">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <p className="text-sm font-medium">All clear</p>
                <p className="text-xs text-[var(--muted-foreground)]">No unresolved alerts.</p>
              </div>
            ) : alerts.slice(0, 6).map((a: any) => (
              <div key={a.id} className="flex items-start gap-2 p-2 rounded-md hover:bg-[var(--accent)] transition-colors">
                <AlertCircle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{a.student_name || "Student"}</div>
                  <div className="text-xs text-[var(--muted-foreground)] line-clamp-2">{a.message?.slice(0, 80) || a.alert_type}</div>
                </div>
                <Badge variant="proxy" className="shrink-0 text-[10px]">{a.alert_type || "alert"}</Badge>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Quick actions</CardTitle>
          <CardDescription>Common faculty tasks</CardDescription>
        </CardHeader>
        <CardContent className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-3">
          {[
            { to: "/sessions", icon: Plus, label: "Start session", desc: "Begin a new class", color: "from-brand-500 to-brand-700" },
            { to: "/attendance", icon: Users, label: "Mark attendance", desc: "Manage records", color: "from-blue-500 to-indigo-600" },
            { to: "/analytics", icon: TrendingUp, label: "Analytics", desc: "Class insights", color: "from-emerald-500 to-teal-600" },
            { to: "/reports", icon: Activity, label: "Reports", desc: "Generate & export", color: "from-amber-500 to-orange-600" },
          ].map(({ to, icon: Icon, label, desc, color }) => (
            <Link key={to} to={to} className="group relative overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-4 transition-all hover:shadow-[var(--shadow-elevated)]">
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
        </CardContent>
      </Card>
    </div>
  );
}
