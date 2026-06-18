import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, Edit, Trash2, Loader2, FolderOpen } from "lucide-react";
import { toast } from "sonner";
import { coursesApi, facultyApi, subjectsApi, departmentsApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
  DialogDescription, DialogFooter,
} from "@/components/ui/dialog";

export function CoursesPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: list = [], isLoading } = useQuery({
    queryKey: ["courses", "list"],
    queryFn: () => coursesApi.list().then((r: any) => extractList(r)),
  });

  const filtered = list.filter((c: any) => {
    if (!q) return true;
    return [c.name, c.code].filter(Boolean).some((v: string) =>
      v.toLowerCase().includes(q.toLowerCase())
    );
  });

  async function remove(c: any) {
    if (!confirm(`Delete course "${c.name}"? This will fail if the course has session history.`)) return;
    try {
      await coursesApi.remove(c.id);
      toast.success("Course deleted");
      qc.invalidateQueries({ queryKey: ["courses"] });
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Courses"
        description="Manage courses and their assigned faculty"
        actions={
          <Button variant="gradient" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add course
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
            <div className="font-semibold">Courses list</div>
            <div className="text-xs text-[var(--muted-foreground)]">{filtered.length} of {list.length}</div>
          </div>
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <FolderOpen className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
              <p className="text-sm font-medium">{list.length === 0 ? "No courses yet" : "No matches"}</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((c: any) => (
                <div key={c.id} className="flex items-center gap-4 py-3 px-1 hover:bg-[var(--accent)] rounded-md transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{c.name}</div>
                    <div className="text-xs text-[var(--muted-foreground)]">{c.code} · Sem {c.semester ?? "—"} · {c.academic_year ?? "—"}</div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setEditId(c.id)}><Edit className="h-3 w-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(c)}><Trash2 className="h-3 w-3 text-red-500" /></Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <CourseDialog open={addOpen} onOpenChange={setAddOpen} onSaved={() => qc.invalidateQueries({ queryKey: ["courses"] })} />
      <CourseDialog open={editId !== null} editId={editId} onOpenChange={(v) => { if (!v) setEditId(null); }} onSaved={() => qc.invalidateQueries({ queryKey: ["courses"] })} />
    </div>
  );
}

function CourseDialog({ open, onOpenChange, editId, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void; editId?: string | null; onSaved: () => void;
}) {
  const { user } = useAuth();
  const isEdit = !!editId;
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [semester, setSemester] = useState("");
  const [academicYear, setAcademicYear] = useState("");
  const [facultyId, setFacultyId] = useState("");
  const [subjectId, setSubjectId] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

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
  const { data: deptList = [] } = useQuery({
    queryKey: ["departments", "list"],
    queryFn: () => departmentsApi.list().then((r: any) => extractList(r)),
    enabled: open,
  });

  const deptId = user?.department_id || (deptList[0] as any)?.id || "";

  if (isEdit && open && !loading && !name) {
    setLoading(true);
    coursesApi.get(editId!)
      .then((c: any) => {
        setName(c.name || ""); setCode(c.code || ""); setSemester(String(c.semester ?? ""));
        setAcademicYear(c.academic_year || ""); setFacultyId(c.faculty_id || "");
        setSubjectId(c.subject_id || ""); setLoading(false);
      })
      .catch(() => setLoading(false));
  }

  function reset() {
    setName(""); setCode(""); setSemester(""); setAcademicYear("");
    setFacultyId(""); setSubjectId(""); setLoading(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !code || !facultyId) { toast.error("Name, code, and faculty are required"); return; }
    setSaving(true);
    try {
      const body: any = {
        name, code,
        institution_id: user?.institution_id,
        department_id: deptId,
        faculty_id: facultyId,
        subject_id: subjectId || undefined,
        semester: semester ? parseInt(semester) : undefined,
        academic_year: academicYear || undefined,
      };
      if (isEdit) {
        await coursesApi.update(editId!, body);
        toast.success("Course updated");
      } else {
        await coursesApi.create(body);
        toast.success("Course added");
      }
      onSaved(); onOpenChange(false); reset();
    } catch (err: any) {
      toast.error(err?.message || "Failed to save");
    } finally { setSaving(false); }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><FolderOpen className="h-4 w-4" /> {isEdit ? "Edit course" : "Add new course"}</DialogTitle>
          <DialogDescription>{isEdit ? "Update course details." : "Create a course and assign it to a faculty member."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="c-name">Name *</Label>
              <Input id="c-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Data Structures" required disabled={loading} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="c-code">Code *</Label>
              <Input id="c-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="CS201" required disabled={loading} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="c-faculty">Faculty *</Label>
              <select value={facultyId} onChange={(e) => setFacultyId(e.target.value)} required className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">Select faculty</option>
                {(facultyList as any[]).map((f: any) => <option key={f.id} value={f.id}>{f.full_name}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="c-subject">Subject</Label>
              <select value={subjectId} onChange={(e) => setSubjectId(e.target.value)} className="h-10 w-full rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">None</option>
                {(subjectList as any[]).map((s: any) => <option key={s.id} value={s.id}>{s.name} ({s.code})</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="c-sem">Semester</Label>
              <Input id="c-sem" type="number" value={semester} onChange={(e) => setSemester(e.target.value)} placeholder="3" />
            </div>
            <div className="space-y-2">
              <Label htmlFor="c-year">Academic year</Label>
              <Input id="c-year" value={academicYear} onChange={(e) => setAcademicYear(e.target.value)} placeholder="2025-26" />
            </div>
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => { onOpenChange(false); reset(); }}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving || loading}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {isEdit ? "Save changes" : "Add course"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
