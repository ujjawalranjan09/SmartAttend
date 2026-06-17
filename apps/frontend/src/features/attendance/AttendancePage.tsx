import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ScanLine, Download, Filter, AlertTriangle } from "lucide-react";
import { attendanceApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { formatDate, attendanceClass } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";
import { AttendanceRing } from "@/components/common/AttendanceRing";

export function AttendancePage() {
  const { user } = useAuth();
  const role = user?.role || "student";
  const [tab, setTab] = useState(role === "student" ? "overview" : "manage");
  const [filters, setFilters] = useState({ course: "", date: "", status: "", flagged: false });

  const { data: records = [], isLoading } = useQuery({
    queryKey: ["attendance", "history", user?.id],
    queryFn: async () => {
      const res = await attendanceApi.history({ limit: 100 });
      return (res as any)?.items || (res as any) || [];
    },
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={role === "student" ? "My Attendance" : "Attendance Management"}
        description={role === "student" ? "Track your attendance across all courses" : "View and manage student attendance with proxy risk indicators"}
        actions={
          role === "student" ? (
            <Button asChild variant="gradient"><Link to="/qr-scanner"><ScanLine /> Mark attendance</Link></Button>
          ) : (
            <Button variant="outline" onClick={async () => {
  try {
    const token = localStorage.getItem("smartattend_token");
    const res = await fetch("/api/v1/reports/export/csv", { headers: { Authorization: `Bearer ${token}` } });
    if (!res.ok) throw new Error(`Export failed: ${res.status}`);
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `attendance-${new Date().toISOString().split("T")[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    toast.success("CSV downloaded");
  } catch (e) {
    toast.error(e instanceof Error ? e.message : "Export failed");
  }
}}><Download /> Export CSV</Button>
          )
        }
      />

      {role === "student" && <StudentView records={records} loading={isLoading} />}
      {role !== "student" && <FacultyView records={records} loading={isLoading} filters={filters} setFilters={setFilters} />}
    </div>
  );
}

import { toast } from "sonner";

function StudentView({ records, loading }: { records: any[]; loading: boolean }) {
  // Group by course
  const courses: Record<string, { present: number; total: number }> = {};
  records.forEach((r) => {
    const key = r.course_name || r.course_id || "Unknown";
    if (!courses[key]) courses[key] = { present: 0, total: 0 };
    courses[key].total++;
    if (r.status === "present") courses[key].present++;
  });

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {loading ? (
          Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-48" />)
        ) : Object.keys(courses).length === 0 ? (
          <div className="col-span-full">
            <EmptyState icon={<ScanLine className="h-6 w-6" />} title="No attendance yet" description="Scan a session QR code to mark your first attendance." />
          </div>
        ) : Object.entries(courses).map(([name, c]) => {
          const pct = c.total ? Math.round((c.present / c.total) * 100) : 0;
          return (
            <Card key={name} className="hover:shadow-[var(--shadow-soft)] transition-all">
              <CardHeader>
                <CardTitle className="text-sm line-clamp-1">{name}</CardTitle>
                <CardDescription>{c.present} of {c.total} classes</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col items-center gap-3">
                <AttendanceRing value={pct} size={120} strokeWidth={10} />
                <Badge variant={pct >= 75 ? "success" : pct >= 60 ? "warning" : "destructive"}>
                  {pct >= 75 ? "Safe" : pct >= 60 ? "At risk" : "Shortage"}
                </Badge>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Recent history</CardTitle>
          <CardDescription>Last {Math.min(records.length, 20)} records</CardDescription>
        </CardHeader>
        <CardContent>
          {records.length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)] py-6 text-center">No records.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)] border-b border-[var(--border)]">
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Course</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2">Method</th>
                  </tr>
                </thead>
                <tbody>
                  {records.slice(0, 20).map((r, i) => (
                    <tr key={i} className="border-b border-[var(--border)] last:border-0 hover:bg-[var(--accent)] transition-colors">
                      <td className="py-2 pr-4">{formatDate(r.marked_at || r.created_at)}</td>
                      <td className="py-2 pr-4">{r.course_name || r.course_id}</td>
                      <td className="py-2 pr-4"><Badge variant={r.status === "present" ? "success" : r.status === "late" ? "warning" : "destructive"}>{r.status}</Badge></td>
                      <td className="py-2"><Badge variant="muted">{r.method || "qr"}</Badge></td>
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

function FacultyView({ records, loading, filters, setFilters }: { records: any[]; loading: boolean; filters: any; setFilters: (f: any) => void }) {
  const proxyCount = records.filter((r) => r.status === "proxy_suspected" || (r.proxy_anomaly_score || 0) > 0.6).length;
  const filtered = records.filter((r) => {
    if (filters.status && r.status !== filters.status) return false;
    if (filters.flagged && !(r.status === "proxy_suspected" || (r.proxy_anomaly_score || 0) > 0.6)) return false;
    return true;
  });

  return (
    <div className="space-y-4">
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              <Filter className="h-3 w-3" /> Filters
            </div>
            <Input placeholder="Course" value={filters.course} onChange={(e) => setFilters({ ...filters, course: e.target.value })} className="max-w-[180px] h-9" />
            <Input type="date" value={filters.date} onChange={(e) => setFilters({ ...filters, date: e.target.value })} className="max-w-[170px] h-9" />
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })} className="h-9 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
              <option value="">All status</option>
              <option value="present">Present</option>
              <option value="absent">Absent</option>
              <option value="late">Late</option>
              <option value="proxy_suspected">Proxy suspected</option>
            </select>
            <label className="flex items-center gap-2 text-sm cursor-pointer ml-auto">
              <input type="checkbox" checked={filters.flagged} onChange={(e) => setFilters({ ...filters, flagged: e.target.checked })} className="h-4 w-4 rounded border-[var(--border)]" />
              <span className="flex items-center gap-1"><AlertTriangle className="h-3 w-3 text-red-500" /> Flagged only</span>
            </label>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle>Attendance records</CardTitle>
              <CardDescription>{filtered.length} record{filtered.length !== 1 ? "s" : ""}</CardDescription>
            </div>
            {proxyCount > 0 && <Badge variant="destructive">{proxyCount} flagged</Badge>}
          </div>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-2">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-12" />)}</div>
          ) : filtered.length === 0 ? (
            <EmptyState title="No records" description="Try clearing filters." />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs uppercase tracking-wider text-[var(--muted-foreground)] border-b border-[var(--border)]">
                    <th className="py-2 pr-4">Student</th>
                    <th className="py-2 pr-4">Course</th>
                    <th className="py-2 pr-4">Date</th>
                    <th className="py-2 pr-4">Status</th>
                    <th className="py-2 pr-4">Face Conf.</th>
                    <th className="py-2">Risk</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((r, i) => {
                    const risk = r.proxy_anomaly_score || r.proxy_risk_score || 0;
                    const isFlagged = r.status === "proxy_suspected" || risk > 0.6;
                    const riskColor = risk > 0.6 ? "text-red-500" : risk > 0.3 ? "text-amber-500" : "text-emerald-500";
                    return (
                      <tr key={i} className={`border-b border-[var(--border)] last:border-0 transition-colors hover:bg-[var(--accent)] ${isFlagged ? "bg-red-500/5" : ""}`}>
                        <td className="py-2 pr-4 font-medium">{r.student_name || r.student_id}</td>
                        <td className="py-2 pr-4">{r.course_name || r.course_id}</td>
                        <td className="py-2 pr-4">{formatDate(r.marked_at || r.created_at)}</td>
                        <td className="py-2 pr-4">
                          <Badge variant={r.status === "present" ? "success" : r.status === "proxy_suspected" ? "proxy" : r.status === "late" ? "warning" : "destructive"}>
                            {r.status === "proxy_suspected" ? "Proxy" : r.status}
                          </Badge>
                        </td>
                        <td className="py-2 pr-4 tabular-nums">{r.face_confidence ? `${(r.face_confidence * 100).toFixed(0)}%` : "—"}</td>
                        <td className={`py-2 font-semibold tabular-nums ${riskColor}`}>{Math.round(risk * 100)}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
