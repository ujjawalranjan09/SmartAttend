import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { Users, GraduationCap, Percent, AlertTriangle, Activity, TrendingUp, ChevronRight, Sparkles } from "lucide-react";
import { analyticsApi, studentsApi } from "@/lib/api";
import { greeting, formatPercent, extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { KpiCard } from "@/components/common/KpiCard";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function AdminDashboard() {
  const greet = greeting();
  const { data: summary } = useQuery({ queryKey: ["analytics", "summary"], queryFn: () => analyticsApi.summary() });
  const { data: atRisk = [] } = useQuery({
    queryKey: ["analytics", "at-risk"],
    queryFn: async () => {
      try {
        const res = await analyticsApi.atRisk({ limit: 8 });
        return extractList(res);
      } catch { return []; }
    },
  });
  const { data: students = [] } = useQuery({
    queryKey: ["students", "sample"],
    queryFn: async () => {
      try {
        const res = await studentsApi.list({ limit: 100 });
        return extractList(res);
      } catch { return []; }
    },
  });

  const stats = (summary as any) || {};
  const byDept = stats.by_department || [];
  const trend = stats.weekly_trend || [];

  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow={`${greet.emoji} ${greet.text}, Admin`}
        title="Institution overview"
        description={new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}
        actions={
          <Button asChild variant="gradient"><Link to="/students"><Users /> Manage students</Link></Button>
        }
      />

      {stats.at_risk_count > 0 && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 flex items-start gap-3">
          <Sparkles className="h-5 w-5 text-amber-500 mt-0.5 shrink-0" />
          <div className="flex-1">
            <div className="font-semibold text-amber-600 dark:text-amber-400">{stats.at_risk_count} students below 75%</div>
            <div className="text-sm text-amber-600/80 dark:text-amber-400/80 mt-0.5">
              Consider sending attendance reminders or meeting with faculty advisors.
            </div>
          </div>
          <Button asChild size="sm" variant="outline"><Link to="/analytics">View analytics <ChevronRight className="h-3 w-3" /></Link></Button>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <KpiCard label="Total students" value={stats.total_students ?? students.length} icon={Users} variant="brand" />
        <KpiCard label="Faculty" value={stats.total_faculty ?? "—"} icon={GraduationCap} variant="info" />
        <KpiCard label="Avg attendance" value={stats.avg_attendance != null ? formatPercent(stats.avg_attendance) : "—"} icon={Percent} variant={(stats.avg_attendance ?? 0) >= 75 ? "success" : "warning"} />
        <KpiCard label="At-risk students" value={stats.at_risk_count ?? atRisk.length} icon={AlertTriangle} variant={(stats.at_risk_count ?? 0) > 0 ? "error" : "success"} />
        <KpiCard label="Active sessions" value={stats.active_sessions ?? 0} icon={Activity} variant="brand" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Institution trend</CardTitle>
            <CardDescription>Avg attendance, last 8 weeks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {trend.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey={(d: any) => d.label || d.week} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Avg %"]} />
                    <Bar dataKey="pct" fill="#14b8a6" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-sm text-[var(--muted-foreground)]">No data yet</div>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Department comparison</CardTitle>
            <CardDescription>Average attendance by department</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {byDept.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={byDept} layout="vertical" margin={{ top: 5, right: 10, left: 20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" horizontal={false} />
                    <XAxis type="number" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <YAxis type="category" dataKey={(d: any) => d.name || d.department} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} width={60} />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Avg %"]} />
                    <Bar dataKey="pct" fill="#14b8a6" radius={[0, 6, 6, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-sm text-[var(--muted-foreground)]">No data yet</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>At-risk students</CardTitle>
              <CardDescription>Students below the 75% threshold</CardDescription>
            </div>
            <Button asChild variant="ghost" size="sm"><Link to="/analytics">View all <ChevronRight className="h-3 w-3" /></Link></Button>
          </div>
        </CardHeader>
        <CardContent>
          {atRisk.length === 0 ? (
            <div className="text-center py-8">
              <div className="h-12 w-12 rounded-full bg-emerald-500/10 text-emerald-500 flex items-center justify-center mx-auto mb-3">
                <TrendingUp className="h-6 w-6" />
              </div>
              <p className="text-sm font-medium">No at-risk students</p>
              <p className="text-xs text-[var(--muted-foreground)]">Everyone is above 75% — keep it up!</p>
            </div>
          ) : (
            <div className="space-y-1">
              {atRisk.slice(0, 8).map((s: any) => {
                const pct = s.attendance_pct ?? s.percentage ?? 0;
                const cls = pct >= 60 ? "warning" : "destructive";
                return (
                  <div key={s.id || s.student_id} className="flex items-center gap-3 p-2 rounded-md hover:bg-[var(--accent)] transition-colors">
                    <div className="h-8 w-8 rounded-full bg-gradient-to-br from-amber-400 to-red-500 flex items-center justify-center text-white text-xs font-semibold">
                      {(s.full_name || s.student_name || "U").split(" ").map((n: string) => n[0]).slice(0, 2).join("").toUpperCase()}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{s.full_name || s.student_name || "Student"}</div>
                      <div className="text-xs text-[var(--muted-foreground)]">{s.roll_number || ""}</div>
                    </div>
                    <Badge variant={cls}>{pct}%</Badge>
                    {s.classes_needed && (
                      <span className="text-xs text-[var(--muted-foreground)] tabular-nums">+{s.classes_needed} needed</span>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
