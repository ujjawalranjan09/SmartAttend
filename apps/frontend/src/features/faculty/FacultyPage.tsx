import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Search, UserPlus, Mail, Hash, Trash2, Loader2, GraduationCap, Edit } from "lucide-react";
import { toast } from "sonner";
import { facultyApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { initials, extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter } from "@/components/ui/dialog";

export function FacultyPage() {
  const qc = useQueryClient();
  const [q, setQ] = useState("");
  const [addOpen, setAddOpen] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);

  const { data: list = [], isLoading } = useQuery({
    queryKey: ["faculty", "list"],
    queryFn: async () => {
      const r = await facultyApi.list();
      return extractList(r);
    },
  });

  const filtered = list.filter((f: any) => {
    if (!q) return true;
    return [f.full_name, f.email, f.employee_id].filter(Boolean).some((v: string) => v.toLowerCase().includes(q.toLowerCase()));
  });

  async function remove(f: any) {
    if (!confirm(`Remove ${f.full_name}? This will revoke their access immediately.`)) return;
    try {
      await facultyApi.remove(f.id);
      toast.success(`${f.full_name} removed`);
      qc.invalidateQueries({ queryKey: ["faculty"] });
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to remove";
      toast.error(typeof msg === "string" ? msg : "Failed");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Faculty"
        description="Manage faculty accounts and assignments"
        actions={
          <Button variant="gradient" onClick={() => setAddOpen(true)}><UserPlus className="h-4 w-4" /> Add faculty</Button>
        }
      />

      <Card>
        <CardContent className="pt-6">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[var(--muted-foreground)]" />
            <Input placeholder="Search by name, email, or employee ID..." value={q} onChange={(e) => setQ(e.target.value)} className="pl-9" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-3">
            <div className="font-semibold">Faculty list</div>
            <div className="text-xs text-[var(--muted-foreground)]">{filtered.length} of {list.length}</div>
          </div>

          {isLoading ? (
            <div className="space-y-2">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
          ) : filtered.length === 0 ? (
            <div className="py-12 text-center">
              <GraduationCap className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
              <p className="text-sm font-medium">{list.length === 0 ? "No faculty yet" : "No matches"}</p>
              <p className="text-xs text-[var(--muted-foreground)] mt-1">{list.length === 0 ? "Add your first faculty member to get started" : "Try adjusting your search"}</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--border)]">
              {filtered.map((f: any) => (
                <div key={f.id} className="flex items-center gap-4 py-3 px-1 hover:bg-[var(--accent)] rounded-md transition-colors">
                  <div className="h-10 w-10 rounded-full bg-gradient-to-br from-blue-400 to-blue-600 flex items-center justify-center text-white font-semibold shrink-0">
                    {initials(f.full_name)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="font-medium truncate flex items-center gap-2">
                      {f.full_name}
                      {!f.is_active && <Badge variant="muted">Inactive</Badge>}
                    </div>
                    <div className="text-xs text-[var(--muted-foreground)] flex items-center gap-3 mt-0.5">
                      {f.employee_id && <span className="flex items-center gap-1"><Hash className="h-3 w-3" /> {f.employee_id}</span>}
                      {f.email && <span className="flex items-center gap-1 truncate"><Mail className="h-3 w-3" /> {f.email}</span>}
                    </div>
                  </div>
                  <Button size="sm" variant="ghost" onClick={() => setEditId(f.id)}><Edit className="h-3 w-3" /></Button>
                  <Button size="sm" variant="ghost" onClick={() => remove(f)}><Trash2 className="h-3 w-3 text-red-500" /></Button>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <FacultyDialog open={addOpen} onOpenChange={setAddOpen} onSaved={() => qc.invalidateQueries({ queryKey: ["faculty"] })} />
      <FacultyDialog open={editId !== null} editId={editId} onOpenChange={(v) => { if (!v) setEditId(null); }} onSaved={() => qc.invalidateQueries({ queryKey: ["faculty"] })} />
    </div>
  );
}

function FacultyDialog({ open, onOpenChange, editId, onSaved }: { open: boolean; onOpenChange: (v: boolean) => void; editId?: string | null; onSaved: () => void }) {
  const { user } = useAuth();
  const isEdit = !!editId;
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [employeeId, setEmployeeId] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);

  // Load faculty on edit open
  if (isEdit && open && !loading && !fullName) {
    setLoading(true);
    facultyApi.list().then((r: any) => {
      const list = extractList(r) as any[];
      const f = list.find((x: any) => x.id === editId);
      if (f) {
        setFullName(f.full_name || "");
        setEmail(f.email || "");
        setEmployeeId(f.employee_id || "");
        setPhone(f.phone || "");
      }
      setLoading(false);
    }).catch(() => setLoading(false));
  }

  function reset() {
    setFullName(""); setEmail(""); setEmployeeId(""); setPhone(""); setPassword(""); setLoading(false);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!fullName || !email) { toast.error("Name and email are required"); return; }
    if (!isEdit && password.length < 8) { toast.error("Password must be at least 8 characters"); return; }
    setSaving(true);
    try {
      if (isEdit) {
        await facultyApi.update(editId!, {
          full_name: fullName,
          email,
          phone: phone || undefined,
          employee_id: employeeId || undefined,
        });
        toast.success("Faculty updated");
      } else {
        await facultyApi.create({
          full_name: fullName,
          email,
          password,
          phone: phone || undefined,
          employee_id: employeeId || undefined,
          role: "faculty",
          institution_id: user?.institution_id,
        });
        toast.success("Faculty added");
      }
      onSaved();
      onOpenChange(false);
      reset();
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to save";
      toast.error(typeof msg === "string" ? msg : "Failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { onOpenChange(v); if (!v) reset(); }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><UserPlus className="h-4 w-4" /> {isEdit ? "Edit faculty" : "Add new faculty"}</DialogTitle>
          <DialogDescription>{isEdit ? "Update faculty details." : "The faculty member can sign in with the email and password you set."}</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="f-name">Full name *</Label>
            <Input id="f-name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Prof. Ramesh Sharma" required disabled={loading} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-2">
              <Label htmlFor="f-email">Email *</Label>
              <Input id="f-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="faculty@school.in" required disabled={loading || isEdit} />
              {isEdit && <div className="text-xs text-[var(--muted-foreground)]">Email cannot be changed</div>}
            </div>
            <div className="space-y-2">
              <Label htmlFor="f-emp">Employee ID</Label>
              <Input id="f-emp" value={employeeId} onChange={(e) => setEmployeeId(e.target.value)} placeholder="EMP-042" disabled={loading} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="f-phone">Phone</Label>
            <Input id="f-phone" type="tel" value={phone} onChange={(e) => setPhone(e.target.value)} placeholder="+91 XXXXXXXXXX" disabled={loading} />
          </div>
          {!isEdit && (
            <div className="space-y-2">
              <Label htmlFor="f-pwd">Temporary password *</Label>
              <Input id="f-pwd" type="text" value={password} onChange={(e) => setPassword(e.target.value)} placeholder="Min 8 characters" required minLength={8} />
              <div className="text-xs text-[var(--muted-foreground)]">Faculty should change this after first login.</div>
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => { onOpenChange(false); reset(); }}>Cancel</Button>
            <Button type="submit" variant="gradient" disabled={saving || loading}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              {isEdit ? "Save changes" : "Add faculty"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
