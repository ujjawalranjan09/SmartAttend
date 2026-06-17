import { useQuery } from "@tanstack/react-query";
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { TrendingUp, TrendingDown, Minus, Sparkles } from "lucide-react";
import { analyticsApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

export function AnalyticsPage() {
  const { user } = useAuth();
  const role = user?.role || "student";

  if (role === "student") return <StudentAnalytics userId={user?.id} />;
  return <AdminAnalytics />;
}

function StudentAnalytics({ userId }: { userId?: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["analytics", "student", userId], queryFn: () => analyticsApi.student(userId) });
  const weekly = (data as any)?.weekly_trend || [];
  const courses = (data as any)?.by_course || [];
  const forecast = (data as any)?.forecast_trend || [];
  const trend = (data as any)?.forecast_trend_direction;
  const next7d = (data as any)?.forecast_7d_pct;
  const TrendIcon = trend === "improving" ? TrendingUp : trend === "declining" ? TrendingDown : Minus;
  const trendColor = trend === "improving" ? "text-emerald-500" : trend === "declining" ? "text-red-500" : "text-[var(--muted-foreground)]";

  return (
    <div className="space-y-6">
      <PageHeader title="My Progress" description="Track your academic attendance over time" />

      {(data as any)?.at_risk_alert && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 flex items-start gap-3">
          <Sparkles className="h-5 w-5 text-red-500 mt-0.5" />
          <div>
            <div className="font-semibold text-red-600 dark:text-red-400">Low attendance alert</div>
            <div className="text-sm text-red-600/80 dark:text-red-400/80 mt-0.5">
              You're at {(data as any).overall_percentage}% — below the 75% threshold. Attend <strong>{(data as any).classes_needed || "?"} more classes</strong> to recover.
            </div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Weekly trend</CardTitle>
            <CardDescription>Last 8 weeks</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {isLoading ? <Skeleton className="h-full" /> : weekly.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={weekly} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="trendA" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#14b8a6" stopOpacity={0.4} />
                        <stop offset="100%" stopColor="#14b8a6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey={(d: any) => d.label || d.week} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Attendance"]} />
                    <Area type="monotone" dataKey="pct" stroke="#14b8a6" strokeWidth={2.5} fill="url(#trendA)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div className="h-full grid place-items-center text-sm text-[var(--muted-foreground)]">No data</div>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <div className="flex items-start justify-between">
              <div>
                <CardTitle>14-day forecast</CardTitle>
                <CardDescription>ML-powered projection</CardDescription>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold tabular-nums">{next7d ?? "—"}%</div>
                <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
                  <TrendIcon className="h-3 w-3" /> {trend || "stable"}
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {forecast.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={forecast} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey="label" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${Math.round(v)}%`, "Forecast"]} />
                    <Line type="monotone" dataKey="predicted_pct" stroke="#10b981" strokeWidth={2.5} strokeDasharray="5 5" dot={{ r: 3, fill: "#10b981" }} />
                    <Line type="monotone" dataKey="upper_bound" stroke="transparent" />
                    <Line type="monotone" dataKey="lower_bound" stroke="transparent" />
                  </LineChart>
                </ResponsiveContainer>
              ) : <div className="h-full grid place-items-center text-sm text-[var(--muted-foreground)]">No forecast yet</div>}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Course-wise breakdown</CardTitle>
          <CardDescription>Attendance per enrolled course</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="h-64">
            {courses.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={courses} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                  <XAxis dataKey="course_name" stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                  <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                  <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Attendance"]} />
                  <Bar dataKey="percentage" radius={[6, 6, 0, 0]}>
                    {courses.map((c: any, i: number) => (
                      <Cell key={i} fill={c.percentage >= 75 ? "#10b981" : c.percentage >= 60 ? "#f59e0b" : "#ef4444"} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="h-full grid place-items-center text-sm text-[var(--muted-foreground)]">No course data</div>}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AdminAnalytics() {
  const { data: summary } = useQuery({ queryKey: ["analytics", "summary"], queryFn: () => analyticsApi.summary() });
  const { data: atRisk = [] } = useQuery({
    queryKey: ["analytics", "at-risk"],
    queryFn: async () => {
      try {
        const res = await analyticsApi.atRisk({ limit: 20 });
        return (res as any)?.items || (res as any) || [];
      } catch { return []; }
    },
  });

  const s = (summary as any) || {};
  const trend = s.weekly_trend || [];
  const byDept = s.by_department || [];

  return (
    <div className="space-y-6">
      <PageHeader title="Analytics" description="Institution attendance insights and trends" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Institution trend</CardTitle><CardDescription>Avg attendance, last 8 weeks</CardDescription></CardHeader>
          <CardContent>
            <div className="h-64">
              {trend.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={trend} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                    <defs><linearGradient id="trendB" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#14b8a6" stopOpacity={0.4} /><stop offset="100%" stopColor="#14b8a6" stopOpacity={0} /></linearGradient></defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
                    <XAxis dataKey={(d: any) => d.label || d.week} stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} />
                    <YAxis stroke="var(--muted-foreground)" fontSize={11} tickLine={false} axisLine={false} domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: "var(--popover)", border: "1px solid var(--border)", borderRadius: 8, fontSize: 12 }} formatter={(v: number) => [`${v}%`, "Avg %"]} />
                    <Area type="monotone" dataKey="pct" stroke="#14b8a6" strokeWidth={2.5} fill="url(#trendB)" />
                  </AreaChart>
                </ResponsiveContainer>
              ) : <div className="h-full grid place-items-center text-sm text-[var(--muted-foreground)]">No data</div>}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Department comparison</CardTitle><CardDescription>Average by department</CardDescription></CardHeader>
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
              ) : <div className="h-full grid place-items-center text-sm text-[var(--muted-foreground)]">No data</div>}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div><CardTitle>At-risk students</CardTitle><CardDescription>Below 75% threshold</CardDescription></div>
            <Badge variant="destructive">{atRisk.length} students</Badge>
          </div>
        </CardHeader>
        <CardContent>
          {atRisk.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)] py-6 text-center">No at-risk students.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)] border-b border-[var(--border)]">
                  <th className="py-2 pr-4">Student</th><th className="py-2 pr-4">Roll No.</th><th className="py-2 pr-4">Attendance</th><th className="py-2 pr-4">Needed</th>
                </tr></thead>
                <tbody>
                  {atRisk.map((s: any, i: number) => (
                    <tr key={i} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--accent)] transition-colors">
                      <td className="py-2 pr-4 font-medium">{s.full_name || s.student_name}</td>
                      <td className="py-2 pr-4"><code className="text-xs font-mono px-1.5 py-0.5 rounded bg-[var(--muted)]">{s.roll_number || "—"}</code></td>
                      <td className="py-2 pr-4"><Badge variant={(s.attendance_pct || s.percentage || 0) >= 60 ? "warning" : "destructive"}>{s.attendance_pct || s.percentage || 0}%</Badge></td>
                      <td className="py-2 pr-4 tabular-nums">{s.classes_needed || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
