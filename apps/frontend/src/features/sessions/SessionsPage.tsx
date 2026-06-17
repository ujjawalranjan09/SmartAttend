import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Calendar, Plus, QrCode, Monitor, StopCircle, Play, Filter, X, Loader2 } from "lucide-react";
import { toast } from "sonner";
import { sessionsApi, coursesApi, displayApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { formatDateTime } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { EmptyState } from "@/components/ui/empty-state";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

const statusVariant: Record<string, any> = {
  active: "success",
  scheduled: "default",
  completed: "muted",
  cancelled: "destructive",
  ended: "muted",
};

export function SessionsPage() {
  const { user } = useAuth();
  const role = user?.role || "student";
  const [filter, setFilter] = useState({ course: "", status: "", date: "" });
  const [createOpen, setCreateOpen] = useState(false);

  const { data: sessions = [], isLoading, refetch } = useQuery({
    queryKey: ["sessions", "list"],
    queryFn: async () => {
      const res = await sessionsApi.list();
      return Array.isArray(res) ? res : (res as any)?.items || [];
    },
  });

  const filtered = sessions.filter((s: any) => {
    if (filter.course && !(s.course_name || s.course_id || "").toString().toLowerCase().includes(filter.course.toLowerCase())) return false;
    if (filter.status && s.status !== filter.status) return false;
    if (filter.date) {
      const dt = new Date(s.start_time || s.started_at || s.created_at || 0).toISOString().split("T")[0];
      if (dt !== filter.date) return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={role === "student" ? "My Schedule" : "Sessions"}
        description={role === "student" ? "Your upcoming and past classes" : "Manage and monitor class sessions"}
        actions={role !== "student" && (
          <Button variant="gradient" onClick={() => setCreateOpen(true)}><Plus /> Create session</Button>
        )}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)]">
              <Filter className="h-3 w-3" /> Filters
            </div>
            <Input placeholder="Course" value={filter.course} onChange={(e) => setFilter((f) => ({ ...f, course: e.target.value }))} className="max-w-[180px] h-9" />
            <select value={filter.status} onChange={(e) => setFilter((f) => ({ ...f, status: e.target.value }))} className="h-9 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
              <option value="">All status</option>
              <option value="active">Active</option>
              <option value="scheduled">Scheduled</option>
              <option value="ended">Ended</option>
            </select>
            <Input type="date" value={filter.date} onChange={(e) => setFilter((f) => ({ ...f, date: e.target.value }))} className="max-w-[170px] h-9" />
            {(filter.course || filter.status || filter.date) && (
              <Button variant="ghost" size="sm" onClick={() => setFilter({ course: "", status: "", date: "" })}>Clear</Button>
            )}
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-44" />)}
        </div>
      ) : filtered.length === 0 ? (
        <EmptyState
          icon={<Calendar className="h-6 w-6" />}
          title={sessions.length === 0 ? "No sessions yet" : "No sessions match"}
          description={sessions.length === 0 ? (role === "student" ? "Your faculty will create sessions" : "Create your first session to get started") : "Try adjusting the filters above."}
          action={sessions.length === 0 && role !== "student" ? (
            <Button variant="gradient" onClick={() => setCreateOpen(true)}><Plus /> Create session</Button>
          ) : undefined}
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((s: any) => <SessionCard key={s.id} session={s} role={role} onChanged={refetch} />)}
        </div>
      )}

      <CreateSessionDialog open={createOpen} onOpenChange={setCreateOpen} onCreated={refetch} />
    </div>
  );
}

function SessionCard({ session: s, role, onChanged }: { session: any; role: string; onChanged: () => void }) {
  const [qrOpen, setQrOpen] = useState(false);
  const [displayOpen, setDisplayOpen] = useState(false);
  const present = s.present_count ?? s.attendance_count ?? 0;
  const enrolled = s.total_enrolled ?? s.enrolled_count ?? 0;
  const pct = enrolled > 0 ? Math.round((present / enrolled) * 100) : 0;
  const startTime = s.start_time || s.started_at || s.created_at;
  const isActive = s.status === "active";

  async function endSession() {
    if (!confirm("End this session? Students will no longer be able to mark attendance.")) return;
    try {
      await sessionsApi.end(s.id);
      toast.success("Session ended");
      onChanged();
    } catch (err: any) {
      toast.error(err?.message || "Failed to end session");
    }
  }

  return (
    <Card className="group hover:shadow-[var(--shadow-soft)] transition-all">
      <div className={`h-1 rounded-t-xl ${isActive ? "bg-emerald-500" : s.status === "scheduled" ? "bg-brand-500" : "bg-neutral-300 dark:bg-neutral-700"}`} />
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="line-clamp-1">{s.course_name || s.course_id || "Session"}</CardTitle>
            <CardDescription>{formatDateTime(startTime)}</CardDescription>
          </div>
          <Badge variant={statusVariant[s.status] || "muted"} className="capitalize shrink-0">{s.status || "unknown"}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          <div className="text-center p-2 rounded-lg bg-[var(--muted)]">
            <div className="text-xl font-bold tabular-nums">{present}</div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mt-0.5">Present</div>
          </div>
          <div className="text-center p-2 rounded-lg bg-[var(--muted)]">
            <div className="text-xl font-bold tabular-nums">{enrolled || "—"}</div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mt-0.5">Enrolled</div>
          </div>
          <div className="text-center p-2 rounded-lg bg-[var(--muted)]">
            <div className={`text-xl font-bold tabular-nums ${pct >= 75 ? "text-emerald-500" : pct >= 60 ? "text-amber-500" : "text-red-500"}`}>{enrolled ? `${pct}%` : "—"}</div>
            <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mt-0.5">Rate</div>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          {isActive && (
            <Button size="sm" variant="default" onClick={() => setQrOpen(true)} className="flex-1"><QrCode className="h-3 w-3" /> Show QR</Button>
          )}
          {isActive && role !== "student" && (
            <>
              <Button size="sm" variant="outline" onClick={() => setDisplayOpen(true)} title="Open classroom display"><Monitor className="h-3 w-3" /></Button>
              <Button size="sm" variant="outline" onClick={endSession} title="End session"><StopCircle className="h-3 w-3" /></Button>
            </>
          )}
        </div>
      </CardContent>

      <QrDialog open={qrOpen} onOpenChange={setQrOpen} session={s} />
      <DisplayDialog open={displayOpen} onOpenChange={setDisplayOpen} session={s} />
    </Card>
  );
}

function CreateSessionDialog({ open, onOpenChange, onCreated }: { open: boolean; onOpenChange: (v: boolean) => void; onCreated: () => void }) {
  const { user } = useAuth();
  const [courseId, setCourseId] = useState("");
  const [meetingUrl, setMeetingUrl] = useState("");
  const [isOnline, setIsOnline] = useState(false);
  const [rotation, setRotation] = useState(30);
  const [saving, setSaving] = useState(false);

  const { data: courses = [] } = useQuery({
    queryKey: ["courses", "list"],
    queryFn: async () => {
      const r = await coursesApi.list();
      return Array.isArray(r) ? r : (r as any)?.items || [];
    },
    enabled: open,
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!courseId) { toast.error("Pick a course first"); return; }
    setSaving(true);
    try {
      await sessionsApi.start({
        course_id: courseId,
        faculty_id: user?.id || "",
        is_online: isOnline,
        meeting_url: meetingUrl || undefined,
        qr_rotation_interval_sec: rotation,
      });
      toast.success("Session started — QR code is now live");
      onCreated();
      onOpenChange(false);
      setCourseId(""); setMeetingUrl(""); setIsOnline(false); setRotation(30);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to start session";
      toast.error(typeof msg === "string" ? msg : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Play className="h-4 w-4" /> Start a new session</DialogTitle>
          <DialogDescription>Select a course and the QR code goes live immediately for students to scan.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="course">Course *</Label>
            <select id="course" value={courseId} onChange={(e) => setCourseId(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm" required>
              <option value="">Select a course…</option>
              {courses.map((c: any) => (
                <option key={c.id} value={c.id}>{c.name || c.code || c.id}</option>
              ))}
            </select>
            {courses.length === 0 && <div className="text-xs text-amber-500">No courses found — contact admin to assign you a course.</div>}
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={isOnline} onChange={(e) => setIsOnline(e.target.checked)} className="h-4 w-4 rounded border-[var(--border)] accent-brand-500" />
            <span className="text-sm">Online / hybrid class</span>
          </label>

          {isOnline && (
            <div className="space-y-2">
              <Label htmlFor="meeting">Meeting URL</Label>
              <Input id="meeting" placeholder="https://meet.google.com/…" value={meetingUrl} onChange={(e) => setMeetingUrl(e.target.value)} />
            </div>
          )}

          <div className="space-y-2">
            <Label htmlFor="rot">QR rotation interval (seconds)</Label>
            <Input id="rot" type="number" min={10} max={300} value={rotation} onChange={(e) => setRotation(parseInt(e.target.value) || 30)} />
            <div className="text-xs text-[var(--muted-foreground)]">How often the QR code regenerates. Lower = more secure against sharing.</div>
          </div>

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving || !courseId}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Start session
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function QrDialog({ open, onOpenChange, session }: { open: boolean; onOpenChange: (v: boolean) => void; session: any }) {
  const { data: qr } = useQuery({
    queryKey: ["session-qr", session.id],
    queryFn: () => sessionsApi.qr(session.id),
    enabled: open,
    refetchInterval: 30_000,
  });

  const qrData = (qr as any)?.qr_data || (qr as any)?.qr_token || "";
  const expiresIn = (qr as any)?.expires_in_seconds || 120;
  const qrImgUrl = qrData ? `https://api.qrserver.com/v1/create-qr-code/?size=240x240&data=${encodeURIComponent(qrData)}` : "";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Session QR Code</DialogTitle>
          <DialogDescription>Students scan this code to mark attendance. Rotates every {expiresIn}s.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col items-center gap-4 py-2">
          {qrImgUrl ? (
            <div className="p-4 rounded-2xl bg-white shadow-sm">
              <img src={qrImgUrl} alt="QR code" className="h-48 w-48" />
            </div>
          ) : (
            <div className="h-48 w-48 grid place-items-center bg-[var(--muted)] rounded-xl">
              <Loader2 className="h-6 w-6 animate-spin text-[var(--muted-foreground)]" />
            </div>
          )}
          <div className="text-center">
            <div className="text-sm font-medium">{session.course_name || session.course_id}</div>
            <Badge variant="success" className="mt-1">Active</Badge>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Close</Button>
          <Button onClick={() => { navigator.clipboard.writeText(qrData); toast.success("Copied!"); }} disabled={!qrData}>Copy QR data</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function DisplayDialog({ open, onOpenChange, session }: { open: boolean; onOpenChange: (v: boolean) => void; session: any }) {
  const [token, setToken] = useState<string | null>(null);
  const [url, setUrl] = useState("");

  async function load() {
    try {
      const res = await displayApi.getToken(session.id);
      const t = (res as any).display_token;
      setToken(t);
      const apiOrigin = window.location.origin.replace(/\/$/, "");
      setUrl(`${apiOrigin}/classroom-display.html?session_id=${session.id}&token=${t}`);
    } catch (err: any) {
      toast.error(err?.message || "Failed to get display token");
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (v) load(); }}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Classroom display</DialogTitle>
          <DialogDescription>Project this URL on the classroom screen so students see attendance update in real-time.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Input value={url} readOnly placeholder={token ? "" : "Generating link..."} />
          <div className="flex gap-2">
            <Button variant="outline" className="flex-1" disabled={!url} onClick={async () => { await navigator.clipboard.writeText(url); toast.success("Copied!"); }}>Copy link</Button>
            <Button variant="gradient" className="flex-1" disabled={!url} onClick={() => window.open(url, "_blank")}>Open in new tab</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
