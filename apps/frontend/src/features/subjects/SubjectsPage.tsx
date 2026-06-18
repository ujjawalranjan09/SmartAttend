import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, Plus, Edit, Trash2, Loader2, BookOpen } from "lucide-react";
import { toast } from "sonner";
import { subjectsApi } from "@/lib/api";
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
import { useAuth } from "@/store/auth";

export function SubjectsPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: list = [], isLoading } = useQuery({
    queryKey: ["subjects", "list"],
    queryFn: () => subjectsApi.list().then((r: any) => extractList(r)),
  });

  const filtered = list.filter((s: any) => {
    if (!q) return true;
    return [s.name, s.code].filter(Boolean).some((v: string) =>
      v.toLowerCase().includes(q.toLowerCase())
    );
  });

  async function remove(s: any) {
    if (!confirm(`Delete subject "${s.name}"?`)) return;
    try {
      await subjectsApi.remove(s.id);
      toast.success("Subject deleted");
      qc.invalidateQueries({ queryKey: ["subjects"] });
    } catch (err: any) {
      toast.error(err?.message || "Failed to delete");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Subjects"
        description="Manage the catalog of subjects taught at your institution"
        actions={
          <Button variant="gradient" onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add subject
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
            <div className="font-semibold">Subjects list</div>
            <div className="text-xs text-[var(--muted-foreground)]">{filtered.length} of {list.length}</div>
          </div>
          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-14" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <BookOpen className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
              <p className="text-sm font-medium">{list.length === 0 ? "No subjects yet" : "No matches"}</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((s: any) => (
                <div key={s.id} className="flex items-center gap-4 py-3 px-1 hover:bg-[var(--accent)] rounded-md transition-colors">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate">{s.name}</div>
                    <div className="text-xs text-[var(--muted-foreground)]">{s.code}</div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setEditId(s.id)}><Edit className="h-3 w-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(s)}><Trash2 className="h-3 w-3 text-red-500" /></Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <SubjectDialog open={addOpen} onOpenChange={setAddOpen} onSaved={() => qc.invalidateQueries({ queryKey: ["subjects"] })} />
      <SubjectDialog open={editId !== null} editId={editId} onOpenChange={(v) => { if (!v) setEditId(null); }} onSaved={() => qc.invalidateQueries({ queryKey: ["subjects"] })} />
    </div>
  );
}

function SubjectDialog({ open, onOpenChange, editId, onSaved }: {
  open: boolean; onOpenChange: (v: boolean) => void; editId?: string | null; onSaved: () => void;
}) {
  const { user } = useAuth();
  const isEdit = !!editId;
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  if (isEdit && open && !loading && !name) {
    setLoading(true);
    subjectsApi.get(editId!)
      .then((s: any) => { setName(s.name || ""); setCode(s.code || ""); setLoading(false); })
      .catch(() => setLoading(false));
  }

  function reset() { setName(""); setCode(""); setLoading(false); }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!name || !code) { toast.error("Name and code are required"); return; }
    setSaving(true);
    try {
      if (isEdit) {
        await subjectsApi.update(editId!, { name, code });
        toast.success("Subject updated");
      } else {
        await subjectsApi.create({ name, code, institution_id: user?.institution_id });
        toast.success("Subject added");
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
          <DialogTitle className="flex items-center gap-2"><BookOpen className="h-4 w-4" /> {isEdit ? "Edit subject" : "Add new subject"}</DialogTitle>
          <DialogDescription>{isEdit ? "Update subject details." : "Add a subject to the catalog."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="sub-name">Name *</Label>
            <Input id="sub-name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Mathematics" required disabled={loading} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="sub-code">Code *</Label>
            <Input id="sub-code" value={code} onChange={(e) => setCode(e.target.value)} placeholder="MATH101" required disabled={loading} />
          </div>
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => { onOpenChange(false); reset(); }}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving || loading}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
              {isEdit ? "Save changes" : "Add subject"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
