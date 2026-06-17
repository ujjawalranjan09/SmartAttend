import { useState } from "react";
import { FileDown, Download, Calendar, AlertTriangle, BarChart3, Loader2, CheckCircle2, Clock, XCircle } from "lucide-react";
import { toast } from "sonner";
import { reportsApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

// Backend ReportRequest.report_type Literal allows: "student" | "course" | "department" | "institution" | "proxy"
const REPORT_TYPES = [
  { value: "institution", label: "Attendance summary (institution-wide)" },
  { value: "course", label: "Course report" },
  { value: "student", label: "Student-level report" },
  { value: "department", label: "Department report" },
  { value: "proxy", label: "Proxy incidents report" },
];

function todayIso(offsetDays = 0) {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().split("T")[0];
}

export function ReportsPage() {
  const { user } = useAuth();
  const [reportType, setReportType] = useState("institution");
  const [format, setFormat] = useState("csv");
  const [fromDate, setFromDate] = useState(todayIso(-30));
  const [toDate, setToDate] = useState(todayIso(0));
  const [generating, setGenerating] = useState(false);
  const [recent, setRecent] = useState<any[]>([]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!user?.institution_id) { toast.error("Missing institution ID — re-login"); return; }
    if (!fromDate || !toDate) { toast.error("Please pick a from and to date"); return; }
    setGenerating(true);
    try {
      const result: any = await reportsApi.generate(user.institution_id, {
        report_type: reportType,
        format,
        from_date: fromDate,
        to_date: toDate,
      });
      toast.success("Report queued — check Recent reports below.");
      const id = Date.now();
      setRecent((r) => [
        { id, job_id: result.job_id, report_type: reportType, format, created_at: new Date().toISOString(), status: "queued" },
        ...r,
      ]);
    } catch (err: any) {
      const data = err?.response?.data;
      let msg = err?.message || "Failed to generate report";
      if (data?.detail) {
        if (Array.isArray(data.detail)) msg = data.detail.map((d: any) => `${d.loc?.join(".")}: ${d.msg}`).join("; ");
        else if (typeof data.detail === "string") msg = data.detail;
      }
      toast.error(msg);
    } finally {
      setGenerating(false);
    }
  }

  async function quickExport(kind: "all" | "at-risk" | "monthly") {
    if (!user?.institution_id) { toast.error("Missing institution ID — re-login"); return; }
    try {
      const res = await fetch(reportsApi.exportCsv(user.institution_id), {
        headers: { Authorization: `Bearer ${localStorage.getItem("smartattend_token") || ""}` },
      });
      if (!res.ok) throw new Error(`Export failed (${res.status})`);
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const fname = kind === "all" ? "all-attendance" : kind === "at-risk" ? "at-risk-students" : "monthly-summary";
      a.download = `${fname}-${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success("CSV downloaded");
    } catch (e: any) {
      toast.error(e?.message || "Export failed");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Reports" description="Generate and download attendance reports" />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Generate report</CardTitle><CardDescription>Configure parameters and export</CardDescription></CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="r-type">Report type</Label>
                <select id="r-type" value={reportType} onChange={(e) => setReportType(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                  {REPORT_TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="r-fmt">Format</Label>
                <select id="r-fmt" value={format} onChange={(e) => setFormat(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                  <option value="csv">CSV (Excel compatible)</option>
                  <option value="pdf">PDF</option>
                  <option value="json">JSON</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-2">
                  <Label htmlFor="r-from">From date</Label>
                  <Input id="r-from" type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} required />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="r-to">To date</Label>
                  <Input id="r-to" type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} required />
                </div>
              </div>
              <Button type="submit" variant="gradient" disabled={generating} className="w-full">
                {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileDown className="h-4 w-4" />}
                {generating ? "Generating..." : "Generate report"}
              </Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Quick export</CardTitle><CardDescription>One-click common reports</CardDescription></CardHeader>
            <CardContent className="space-y-2">
              {[
                { label: "Export all attendance (CSV)", icon: Download, color: "from-brand-500 to-brand-700", kind: "all" as const },
                { label: "Export at-risk students", icon: AlertTriangle, color: "from-amber-500 to-orange-600", kind: "at-risk" as const },
                { label: "Export monthly summary", icon: Calendar, color: "from-blue-500 to-indigo-600", kind: "monthly" as const },
              ].map(({ label, icon: Icon, color, kind }) => (
                <button key={label} onClick={() => quickExport(kind)}
                  className="group w-full flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:border-transparent hover:shadow-[var(--shadow-soft)] transition-all text-left">
                  <div className={`h-9 w-9 rounded-lg bg-gradient-to-br ${color} flex items-center justify-center text-white shrink-0`}>
                    <Icon className="h-4 w-4" />
                  </div>
                  <div className="flex-1 text-sm font-medium">{label}</div>
                  <Download className="h-4 w-4 text-[var(--muted-foreground)] group-hover:text-brand-500 transition-colors" />
                </button>
              ))}
            </CardContent>
          </Card>
        </div>
      </div>

      <Card>
        <CardHeader><CardTitle>Recent reports</CardTitle><CardDescription>Generated reports appear here</CardDescription></CardHeader>
        <CardContent>
          {recent.length === 0 ? (
            <div className="py-8 text-center text-sm text-[var(--muted-foreground)]">No reports generated yet. Configure one above.</div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {recent.map((r) => <RecentReportRow key={r.id} report={r} />)}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function RecentReportRow({ report: r }: { report: any }) {
  const meta: Record<string, { icon: any; color: string; label: string }> = {
    queued: { icon: Clock, color: "warning", label: "Queued" },
    processing: { icon: Loader2, color: "warning", label: "Processing" },
    done: { icon: CheckCircle2, color: "success", label: "Ready" },
    completed: { icon: CheckCircle2, color: "success", label: "Ready" },
    failed: { icon: XCircle, color: "destructive", label: "Failed" },
  };
  const m = meta[r.status] || meta.queued;
  const Icon = m.icon;
  return (
    <div className="flex items-center gap-3 py-3">
      <div className="h-8 w-8 rounded-lg bg-[var(--muted)] grid place-items-center">
        <BarChart3 className="h-4 w-4 text-[var(--muted-foreground)]" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium capitalize">{r.report_type} report</div>
        <div className="text-xs text-[var(--muted-foreground)]">{new Date(r.created_at).toLocaleString()} · {r.format?.toUpperCase()}</div>
      </div>
      <Badge variant={m.color as any}><Icon className="h-3 w-3" /> {m.label}</Badge>
      {r.job_id && (r.status === "done" || r.status === "completed") && (
        <Button size="sm" variant="outline" asChild>
          <a href={reportsApi.downloadUrl(r.job_id)} target="_blank" rel="noreferrer">Download</a>
        </Button>
      )}
    </div>
  );
}
