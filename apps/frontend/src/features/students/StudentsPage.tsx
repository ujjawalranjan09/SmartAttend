import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Download, UserPlus, Users, Mail, Hash, Loader2, Edit, Trash2 } from "lucide-react";
import { toast } from "sonner";
import { studentsApi, reportsApi, batchesApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { initials, attendanceClass, formatPercent, extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

export function StudentsPage() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [filter, setFilter] = useState<"all" | "at-risk" | "safe">("all");
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: studentList = [], isLoading, refetch } = useQuery({
    queryKey: ["students", "list"],
    queryFn: async () => {
      const r = await studentsApi.list();
      return extractList(r);
    },
  });

  const filtered = studentList.filter((s: any) => {
    const matchesQ = !q || [s.full_name, s.roll_number, s.email].filter(Boolean).some((v: string) => v.toLowerCase().includes(q.toLowerCase()));
    const pct = s.attendance_pct ?? 0;
    const matchesFilter = filter === "all" || (filter === "at-risk" ? pct < 75 : pct >= 75);
    return matchesQ && matchesFilter;
  });

  async function remove(s: any) {
    if (!confirm(`Remove ${s.full_name}? This will revoke their access immediately.`)) return;
    try {
      await studentsApi.remove(s.id);
      toast.success(`${s.full_name} removed`);
      qc.invalidateQueries({ queryKey: ["students"] });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to remove";
      toast.error(typeof msg === "string" ? msg : "Failed");
    }
  }

  async function exportCsv() {
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
      a.download = `students-attendance-${new Date().toISOString().split("T")[0]}.csv`;
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
      <PageHeader
        title="Students"
        description="Manage student enrollment and attendance"
        actions={
          <>
            <Button variant="outline" onClick={exportCsv}><Download className="h-4 w-4" /> Export</Button>
            {isAdmin && (
              <Button variant="gradient" onClick={() => setAddOpen(true)}><UserPlus className="h-4 w-4" /> Add student</Button>
            )}
          </>
        }
      />

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 flex-wrap">
            <div className="relative flex-1 min-w-[240px]">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
              <Input placeholder="Search by name, roll number, or email..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" />
            </div>
            <select value={filter} onChange={(e) => setFilter(e.target.value as any)} className="h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
              <option value="all">All students</option>
              <option value="at-risk">At risk (&lt;75%)</option>
              <option value="safe">Safe (≥75%)</option>
            </select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Student list</div>
            <div className="text-xs text-[var(--muted-foreground)]">{filtered.length} of {studentList.length} students</div>
          </div>

          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <Users className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
              <p className="text-sm font-medium">No matches</p>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">Try adjusting your search or filters.</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((s: any) => (
                <div key={s.id} className="flex items-center gap-4 py-3 px-1 hover:bg-[var(--accent)] rounded-md transition-colors">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white font-semibold shrink-0">
                    {initials(s.full_name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{s.full_name}</div>
                    <div className="text-xs text-[var(--muted-foreground)] flex items-center gap-3 mt-0.5">
                      {s.roll_number && <span className="flex items-center gap-1"><Hash className="h-3 w-3" /> {s.roll_number}</span>}
                      {s.email && <span className="flex items-center gap-1 truncate"><Mail className="h-3 w-3" /> {s.email}</span>}
                    </div>
                  </div>
                  {isAdmin && (
                    <>
                      <Button size="sm" variant="ghost" onClick={() => setEditId(s.id)}><Edit className="h-3 w-3" /></Button>
                      <Button size="sm" variant="ghost" onClick={() => remove(s)}><Trash2 className="h-3 w-3 text-red-500" /></Button>
                    </>
                  )}
                  {(() => { const pct = s.attendance_pct ?? null; return pct !== null && (
                    <Badge variant={pct >= 75 ? "success" : pct >= 60 ? "warning" : "destructive"} className="shrink-0 hidden sm:inline-flex">
                      {pct >= 75 ? "Safe" : "At risk"}
                    </Badge>
                  ); })()}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <StudentDialog open={addOpen} onOpenChange={setAddOpen} onSaved={() => { refetch(); qc.invalidateQueries({ queryKey: ["students"] }); }} />
      <StudentDialog open={editId !== null} editId={editId} onOpenChange={(v) => { if (!v) setEditId(null); }} onSaved={() => { refetch(); qc.invalidateQueries({ queryKey: ["students"] }); }} />
    </div>
  );
}

function StudentDialog({ open, onOpenChange, editId, onSaved }: { open: boolean; onOpenChange: (v: boolean) => void; editId?: string | null; onSaved: () => void }) {
  const { user } = useAuth();
  const isEdit = !!editId;
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [password, setPassword] = useState("");
  const [phone, setPhone] = useState("");
  const [batchId, setBatchId] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  const { data: batchList = [] } = useQuery({
    queryKey: ["batches", "list"],
    queryFn: () => batchesApi.list().then((r: any) => extractList(r)),
    enabled: open,
  });

  if (isEdit && open && !loading && !fullName) {
    setLoading(true);
    studentsApi.get(editId!).then((s: any) => {
      setFullName(s.full_name || ""); setEmail(s.email || ""); setRollNumber(s.roll_number || "");
      setPhone(s.phone || ""); setBatchId(s.batch_id || "");
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  function reset() {
    setFullName(""); setEmail(""); setRollNumber(""); setPassword(""); setPhone(""); setBatchId(""); setLoading(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName || !email) { toast.error("Name and email are required"); return; }
    if (!isEdit && password.length < 8) { toast.error("Password must be at least 8 characters"); return; }
    setSaving(true);
    try {
      const data: any = {
        full_name: fullName, email,
        phone: phone || undefined, roll_number: rollNumber || undefined,
        batch_id: batchId || undefined,
      };
      if (!isEdit) { Object.assign(data, { password, role: "student", institution_id: user?.institution_id }); }
      if (isEdit) {
        await studentsApi.update(editId!, data);
        toast.success("Student updated");
      } else {
        await studentsApi.create(data);
        toast.success("Student added");
      }
      reset(); onSaved(); onOpenChange(false);
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed";
      toast.error(typeof msg === "string" ? msg : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><UserPlus className="h-4 w-4" /> {isEdit ? "Edit student" : "Add new student"}</DialogTitle>
          <DialogDescription>{isEdit ? "Update student details." : "The student will be created instantly. They can sign in with the email and password you set."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="s-name">Full name *</Label>
            <Input id="s-name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Priya Sharma" required />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="s-email">Email *</Label>
              <Input id="s-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="student@school.in" required disabled={isEdit} />
              {isEdit && <div className="text-xs text-[var(--muted-foreground)]">Email cannot be changed</div>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="s-roll">Roll number</Label>
              <Input id="s-roll" value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} placeholder="2026-CS-042" />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="s-batch">Batch</Label>
            <select value={batchId} onChange={(e) => setBatchId(e.target.value)} className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
              <option value="">No batch</option>
              {(batchList as any[]).map((b: any) => <option key={b.id} value={b.id}>{b.name} ({b.code})</option>)}
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor="s-phone">Phone</Label>
            <Input id="s-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 XXXXXXXXXX" />
          </div>
          {!isEdit && (
            <div className="space-y-2">
              <Label htmlFor="s-pwd">Temporary password *</Label>
              <Input id="s-pwd" type="text" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 8 characters" required minLength={8} />
              <div className="text-xs text-[var(--muted-foreground)]">The student should change this after first login.</div>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              {isEdit ? "Save changes" : "Add student"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
