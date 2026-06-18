import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Search, Plus, Edit, Trash2, Loader2, Layers, Clock, Users, ChevronDown, ChevronUp, X,
} from "lucide-react";
import { toast } from "sonner";
import { batchesApi, facultyApi, subjectsApi, studentsApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from "@/components/ui/dialog";

const DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

export function BatchesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [scheduleOpen, setScheduleOpen] = useState<string | null>(null);
  const [membersOpen, setMembersOpen] = useState<string | null>(null);

  const { data: list = [], isLoading } = useQuery({
    queryKey: ["batches", "list"],
    queryFn: () => batchesApi.list().then((r: any) => extractList(r)),
  });

  const filtered = list.filter((b: any) => {
    if (!q) return true;
    return [b.name, b.code].filter(Boolean).some((v: string) =>
      v.toLowerCase().includes(q.toLowerCase())
    );
  });

  async function remove(b: any) {
    if (!confirm(`Delete batch "${b.name}"? Students will be unlinked.`)) return;
    try {
      await batchesApi.remove(b.id);
      toast.success("Batch deleted");
      qc.invalidateQueries({ queryKey: ["batches"] });
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete");
    }
  }

  function toggle(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Batches"
        description="Manage student batches and their weekly schedules"
        actions={
          <Button variant="gradient" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add batch
          </Button>
        }
      />
      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
            <Input placeholder="Search by name or code..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" />
          </div>
        </CardContent>
      </Card>
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Batches list</div>
            <div className="text-xs text-[var(--muted-foreground)]">{filtered.length} of {list.length}</div>
          </div>
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <Layers className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
              <p className="text-sm font-medium">{list.length === 0 ? "No batches yet" : "No matches"}</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((b: any) => (
                <div key={b.id}>
                  <div className="flex items-center gap-4 py-3 px-1 hover:bg-[var(--accent)] rounded-md transition-colors">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate flex items-center gap-2">
                        {b.name}
                        {!b.is_active && <Badge variant="muted">Inactive</Badge>}
                      </div>
                      <div className="text-xs text-[var(--muted-foreground)]">
                        {b.code} · Sem {b.semester ?? "—"} · {b.academic_year ?? "—"}
                      </div>
                    </div>
                    <Button size="sm" variant="outline" onClick={() => setScheduleOpen(b.id)}><Clock className="h-3 w-3" /> Schedule</Button>
                    <Button size="sm" variant="outline" onClick={() => setMembersOpen(b.id)}><Users className="h-3 w-3" /> Members</Button>
                    <Button size="sm" variant="ghost" onClick={() => setEditId(b.id)}><Edit className="h-3 w-3" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => remove(b)}><Trash2 className="h-3 w-3 text-red-500" /></Button>
                    <Button size="sm" variant="ghost" onClick={() => toggle(b.id)}>
                      {expandedId === b.id ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
                    </Button>
                  </div>
                  {expandedId === b.id && <ScheduleInline batchId={b.id} />}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <BatchDialog open={addOpen} onOpenChange={setAddOpen} onSaved={() => qc.invalidateQueries({ queryKey: ["batches"] })} />
      <BatchDialog open={editId !== null} editId={editId} onOpenChange={(v) => { if (!v) setEditId(null); }} onSaved={() => qc.invalidateQueries({ queryKey: ["batches"] })} />

      {scheduleOpen && (
        <ScheduleDialog batchId={scheduleOpen} open={true} onOpenChange={(v) => { if (!v) setScheduleOpen(null); }} />
      )}
      {membersOpen && (
        <MembersDialog batchId={membersOpen} open={true} onOpenChange={(v) => { if (!v) setMembersOpen(null); }} />
      )}
    </div>
  );
}

/* ── Inline schedule summary under expanded batch ──────────────────────────── */

function ScheduleInline({ batchId }: { batchId: string }) {
  const { data: schedule = [], isLoading } = useQuery({
    queryKey: ["batch-schedule", batchId],
    queryFn: () => batchesApi.listSchedule(batchId).then((r: any) => extractList(r)),
  });

  return (
    <div className="ml-4 mb-3 p-3 rounded-lg bg-[var(--muted)] text-sm">
      {isLoading ? <Skeleton className="h-4 w-48" /> : schedule.length === 0 ? (
        <span className="text-[var(--muted-foreground)]">No schedule set for this batch.</span>
      ) : (
        <div className="space-y-1">
          {(schedule as any[]).map((s: any) => (
            <div key={s.id} className="flex items-center gap-3">
              <Badge variant="outline">{DAY_NAMES[s.day_of_week] ?? s.day_of_week}</Badge>
              <span>{s.start_time} – {s.end_time}</span>
              <span className="text-[var(--muted-foreground)]">{s.room || "—"}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── Batch create/edit dialog ───────────────────────────────────────────────── */

function BatchDialog({ open, onOpenChange, editId, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void; editId?: string | null; onSaved: () => void;
}) {
  const { user } = useAuth();
  const isEdit = !!editId;
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [semester, setSemester] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  if (isEdit && open && !loading && !name) {
    setLoading(true);
    batchesApi.get(editId!)
      .then((b: any) => {
        setName(b.name || ""); setCode(b.code || "");
        setSemester(String(b.semester ?? "")); setAcademicYear(b.academic_year || "");
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }

  function reset() { setName(""); setCode(""); setSemester(""); setAcademicYear(""); setLoading(false); }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !code) { toast.error("Name and code are required"); return; }
    setSaving(true);
    try {
      const body: any = {
        name, code, institution_id: user?.institution_id,
        semester: semester ? parseInt(semester) : undefined,
        academic_year: academicYear || undefined,
      };
      if (isEdit) { await batchesApi.update(editId!, body); toast.success("Batch updated"); }
      else { await batchesApi.create(body); toast.success("Batch added"); }
      onSaved(); onOpenChange(false); reset();
    } catch (err: any) { toast.error(err?.message || "Failed to save"); }
    finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Layers className="h-4 w-4" /> {isEdit ? "Edit batch" : "Add new batch"}</DialogTitle>
          <DialogDescription>{isEdit ? "Update batch details." : "Create a batch to group students."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="b-name">Name *</Label>
              <Input id="b-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="CSE 2025 - Sec A" required disabled={loading} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="b-code">Code *</Label>
              <Input id="b-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="CSE25-A" required disabled={loading} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="b-sem">Semester</Label>
              <Input id="b-sem" type="number" value={semester} onChange={(e) => setSemester(e.target.value)} placeholder="3" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="b-year">Academic year</Label>
              <Input id="b-year" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="2025-26" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => { onOpenChange(false); reset(); }}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving || loading}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {isEdit ? "Save changes" : "Add batch"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Schedule dialog (add weekly slots to a batch) ──────────────────────────── */

function ScheduleDialog({ batchId, open, onOpenChange }: {
  batchId: string; open: boolean; onOpenChange: (v: boolean) => void;
}) {
  const qc = useQueryClient();
  const [day, setDay] = useState("1");
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [facultyId, setFacultyId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [room, setRoom] = useState("");
  const [saving, setSaving] = useState(false);

  const { data: schedule = [] } = useQuery({
    queryKey: ["batch-schedule", batchId],
    queryFn: () => batchesApi.listSchedule(batchId).then((r: any) => extractList(r)),
    enabled: open,
  });
  const { data: facultyList = [] } = useQuery({
    queryKey: ["faculty", "list"],
    queryFn: () => facultyApi.list().then((r: any) => extractList(r)),
    enabled: open,
  });
  const { data: subjectList = [] } = useQuery({
    queryKey: ["subjects", "list"],
    queryFn: () => subjectsApi.list().then((r: any) => extractList(r)),
    enabled: open,
  });

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!facultyId || !subjectId) { toast.error("Faculty and subject are required"); return; }
    setSaving(true);
    try {
      await batchesApi.createSchedule(batchId, {
        faculty_id: facultyId,
        subject_id: subjectId,
        day_of_week: parseInt(day),
        start_time: startTime,
        end_time: endTime,
        room: room || undefined,
      });
      toast.success("Schedule added");
      setFacultyId(""); setSubjectId(""); setRoom("");
      qc.invalidateQueries({ queryKey: ["batch-schedule", batchId] });
    } catch (err: any) { toast.error(err?.message || "Failed to add schedule"); }
    finally { setSaving(false); }
  }

  async function removeSlot(slotId: string) {
    try {
      await batchesApi.removeSchedule(batchId, slotId);
      toast.success("Slot removed");
      qc.invalidateQueries({ queryKey: ["batch-schedule", batchId] });
    } catch (err: any) { toast.error(err?.message || "Failed to remove"); }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Clock className="h-4 w-4" /> Weekly schedule</DialogTitle>
          <DialogDescription>Add recurring weekly slots for this batch.</DialogDescription>
        </DialogHeader>

        {(schedule as any[]).length > 0 && (
          <div className="space-y-2">
            <div className="text-sm font-medium">Existing slots</div>
            <div className="divide-y divide-[var(--border)]">
              {(schedule as any[]).map((s: any) => (
                <div key={s.id} className="flex items-center gap-3 py-2 text-sm">
                  <Badge variant="outline">{DAY_NAMES[s.day_of_week] ?? s.day_of_week}</Badge>
                  <span>{s.start_time} – {s.end_time}</span>
                  <span className="text-[var(--muted-foreground)]">{s.room || ""}</span>
                  <div className="flex-1" />
                  <Button size="sm" variant="ghost" onClick={() => removeSlot(s.id)}><X className="h-3 w-3 text-red-500" /></Button>
                </div>
              ))}
            </div>
          </div>
        )}

        <form onSubmit={submit} className="space-y-3 border-t pt-4 mt-2">
          <div className="text-sm font-medium">Add new slot</div>
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-2">
              <Label htmlFor="s-day">Day</Label>
              <select value={day} onChange={(e) => setDay(e.target.value)} className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                {DAY_NAMES.map((d, i) => <option key={i} value={i}>{d}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="s-start">Start</Label>
              <Input id="s-start" type="time" value={startTime} onChange={(e) => setStartTime(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="s-end">End</Label>
              <Input id="s-end" type="time" value={endTime} onChange={(e) => setEndTime(e.target.value)} required />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="s-fac">Faculty *</Label>
              <select value={facultyId} onChange={(e) => setFacultyId(e.target.value)} required className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">Select faculty</option>
                {(facultyList as any[]).map((f: any) => <option key={f.id} value={f.id}>{f.full_name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="s-subj">Subject *</Label>
              <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} required className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">Select subject</option>
                {(subjectList as any[]).map((s: any) => <option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="s-room">Room</Label>
            <Input id="s-room" value={room} onChange={(e) => setRoom(e.target.value)} placeholder="Room 101" />
          </div>
          <DialogFooter>
            <Button type="submit" variant="gradient" disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              Add slot
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/* ── Members dialog (assign students to a batch) ─────────────────────────────── */

function MembersDialog({ batchId, open, onOpenChange }: {
  batchId: string; open: boolean; onOpenChange: (v: boolean) => void;
}) {
  const qc = useQueryClient();
  const [saving, setSaving] = useState(false);

  const { data: members = [] } = useQuery({
    queryKey: ["batch-members", batchId],
    queryFn: () => batchesApi.listMembers(batchId),
    enabled: open,
  });
  const { data: allStudents = [] } = useQuery({
    queryKey: ["students", "list"],
    queryFn: () => studentsApi.list().then((r: any) => extractList(r)),
    enabled: open,
  });

  const memberIds = new Set((members as any[]).map((m: any) => m.id));
  const nonMembers = (allStudents as any[]).filter((s: any) => !memberIds.has(s.id));

  async function addMember(studentId: string) {
    setSaving(true);
    try {
      const ids = [...memberIds, studentId];
      await batchesApi.setMembers(batchId, ids);
      toast.success("Student added to batch");
      qc.invalidateQueries({ queryKey: ["batch-members", batchId] });
    } catch (err: any) { toast.error(err?.message || "Failed"); }
    finally { setSaving(false); }
  }

  async function removeMember(studentId: string) {
    setSaving(true);
    try {
      const ids = (members as any[]).filter((m: any) => m.id !== studentId).map((m: any) => m.id);
      await batchesApi.setMembers(batchId, ids);
      toast.success("Student removed from batch");
      qc.invalidateQueries({ queryKey: ["batch-members", batchId] });
    } catch (err: any) { toast.error(err?.message || "Failed"); }
    finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Users className="h-4 w-4" /> Batch members</DialogTitle>
          <DialogDescription>Manage students assigned to this batch.</DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <div className="text-sm font-medium">Current members ({(members as any[]).length})</div>
          {(members as any[]).length === 0 ? (
            <p className="text-sm text-[var(--muted-foreground)]">No students assigned yet.</p>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {(members as any[]).map((m: any) => (
                <div key={m.id} className="flex items-center gap-3 py-2 text-sm">
                  <span className="flex-1">{m.full_name} {m.roll_number ? `(${m.roll_number})` : ""}</span>
                  <Button size="sm" variant="ghost" disabled={saving} onClick={() => removeMember(m.id)}>
                    <X className="h-3 w-3 text-red-500" />
                  </Button>
                </div>
              ))}
            </div>
          )}

          {nonMembers.length > 0 && (
            <>
              <div className="text-sm font-medium mt-4">Add students</div>
              <div className="divide-y divide-[var(--border)]">
                {(nonMembers as any[]).slice(0, 20).map((s: any) => (
                  <div key={s.id} className="flex items-center gap-3 py-2 text-sm">
                    <span className="flex-1">{s.full_name} {s.roll_number ? `(${s.roll_number})` : ""}</span>
                    <Button size="sm" variant="outline" disabled={saving} onClick={() => addMember(s.id)}>
                      <Plus className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
                {nonMembers.length > 20 && (
                  <p className="text-xs text-[var(--muted-foreground)] py-1">...and {nonMembers.length - 20} more</p>
                )}
              </div>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
