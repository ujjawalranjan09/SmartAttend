import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Target, Plus, Trash2, Clock, ChevronDown, ChevronUp, Sparkles, Save, X } from "lucide-react";
import { toast } from "sonner";
import { profileApi, goalsApi, dailyPlanApi } from "@/lib/api";
import { extractList } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Progress } from "@/components/ui/progress";

export function ProfilePage() {
  const [tab, setTab] = useState<"profile" | "goals">("profile");

  return (
    <div className="space-y-6">
      <PageHeader
        title="My Profile"
        description="Your academic identity — interests, strengths, and goals"
      />

      <div className="flex gap-1 border-b border-[var(--border)]">
        {([["profile", "My profile"], ["goals", "My goals"]] as const).map(([id, label]) => (
          <button key={id} onClick={() => setTab(id)} className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors ${tab === id ? "border-brand-500 text-brand-500" : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}>
            {label}
          </button>
        ))}
      </div>

      {tab === "profile" ? <ProfileTab /> : <GoalsTab />}
    </div>
  );
}

function ProfileTab() {
  const { data: profile, isLoading } = useQuery({ queryKey: ["profile", "me"], queryFn: () => profileApi.get() });
  const qc = useQueryClient();
  const [editing, setEditing] = useState(false);
  const [interests, setInterests] = useState<string[]>([]);
  const [strengths, setStrengths] = useState<string[]>([]);
  const [careerGoals, setCareerGoals] = useState<string[]>([]);
  const [studyStyle, setStudyStyle] = useState("");
  const [studyHours, setStudyHours] = useState(2);

  if (isLoading) return <Skeleton className="h-64" />;
  if (!profile && !editing) {
    return (
      <Card>
        <CardHeader><CardTitle>Create your profile</CardTitle><CardDescription>Tell us about yourself so we can personalize your daily plan</CardDescription></CardHeader>
        <CardContent>
          <Button variant="gradient" onClick={() => { setInterests([]); setStrengths([]); setCareerGoals([]); setEditing(true); }}>
            <Plus className="h-4 w-4" /> Get started
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!profile || editing) {
    return <ProfileForm initial={{ interests, strengths, career_goals: careerGoals, preferred_study_style: studyStyle, daily_study_hours_target: studyHours }} onSave={async (data) => {
      try {
        if (profile) {
          await profileApi.update(data);
          toast.success("Profile updated");
        } else {
          await profileApi.create(data);
          toast.success("Profile created");
        }
        await dailyPlanApi.invalidateRoutine().catch(() => {});
        qc.invalidateQueries({ queryKey: ["profile", "me"] });
        setEditing(false);
      } catch (err: any) {
        toast.error(err?.message || "Failed to save");
      }
    }} onCancel={() => setEditing(false)} />;
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div><CardTitle>Profile overview</CardTitle><CardDescription>What we've learned about you</CardDescription></div>
            <Button variant="outline" size="sm" onClick={() => { setInterests(profile.interests || []); setStrengths(profile.strengths || []); setCareerGoals(profile.career_goals || []); setStudyStyle(profile.preferred_study_style || ""); setStudyHours(profile.daily_study_hours_target || 2); setEditing(true); }}>
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {[
            { label: "Interests", items: profile.interests, variant: "default" as const },
            { label: "Strengths", items: profile.strengths, variant: "success" as const },
            { label: "Career goals", items: profile.career_goals, variant: "warning" as const },
          ].map(({ label, items, variant }) => (
            <div key={label}>
              <div className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-2">{label}</div>
              <div className="flex flex-wrap gap-1.5">
                {items?.length ? items.map((t: string) => <Badge key={t} variant={variant}>{t}</Badge>) : <span className="text-sm text-[var(--muted-foreground)]">None set</span>}
              </div>
            </div>
          ))}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-4 border-t border-[var(--border)]">
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-1.5">Study style</div>
              <Badge variant="muted" className="capitalize">{profile.preferred_study_style || "Not set"}</Badge>
            </div>
            <div>
              <div className="text-xs font-semibold uppercase tracking-wider text-[var(--muted-foreground)] mb-1.5">Daily study target</div>
              <div className="text-sm font-medium">{profile.daily_study_hours_target || 2} hours/day</div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProfileForm({ initial, onSave, onCancel }: { initial: any; onSave: (d: any) => void; onCancel: () => void }) {
  const [interestInput, setInterestInput] = useState("");
  const [strengthInput, setStrengthInput] = useState("");
  const [careerInput, setCareerInput] = useState("");
  const [style, setStyle] = useState(initial.preferred_study_style || "");
  const [hours, setHours] = useState(initial.daily_study_hours_target || 2);
  const [interests, setInterests] = useState<string[]>(initial.interests || []);
  const [strengths, setStrengths] = useState<string[]>(initial.strengths || []);
  const [careers, setCareers] = useState<string[]>(initial.career_goals || []);
  const [saving, setSaving] = useState(false);

  function addTag(value: string, list: string[], setter: (s: string[]) => void) {
    const v = value.trim();
    if (v && !list.includes(v)) setter([...list, v]);
  }

  return (
    <Card>
      <CardHeader><CardTitle>{initial.interests?.length ? "Edit profile" : "Create your profile"}</CardTitle></CardHeader>
      <CardContent>
        <form onSubmit={async (e) => {
          e.preventDefault();
          setSaving(true);
          try { await onSave({ interests, strengths, career_goals: careers, preferred_study_style: style || undefined, daily_study_hours_target: hours }); }
          finally { setSaving(false); }
        }} className="space-y-5">
          <TagInput label="Interests" tags={interests} onChange={setInterests} input={interestInput} setInput={setInterestInput} placeholder="machine learning, web dev" />
          <TagInput label="Strengths" tags={strengths} onChange={setStrengths} input={strengthInput} setInput={setStrengthInput} placeholder="mathematics, programming" />
          <TagInput label="Career goals" tags={careers} onChange={setCareers} input={careerInput} setInput={setCareerInput} placeholder="software engineer, data analyst" />
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Study style</Label>
              <select value={style} onChange={(e) => setStyle(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">Select…</option>
                {["visual", "reading", "hands-on", "group", "mixed"].map((s) => <option key={s} value={s} className="capitalize">{s}</option>)}
              </select>
            </div>
            <div className="space-y-2">
              <Label>Daily study target (hours)</Label>
              <Input type="number" min={1} max={12} value={hours} onChange={(e) => setHours(parseInt(e.target.value) || 2)} />
            </div>
          </div>
          <div className="flex gap-2">
            <Button type="submit" variant="gradient" disabled={saving}><Save className="h-4 w-4" /> {saving ? "Saving..." : initial.interests?.length ? "Update" : "Create"}</Button>
            <Button type="button" variant="ghost" onClick={onCancel}>Cancel</Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}

function TagInput({ label, tags, onChange, input, setInput, placeholder }: any) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-1.5 p-2 rounded-md border border-[var(--border)] bg-[var(--background)] min-h-[42px] focus-within:ring-2 focus-within:ring-brand-500/30 focus-within:border-brand-500 transition-all">
        {tags.map((t: string) => (
          <Badge key={t} variant="default" className="gap-1">
            {t}
            <button type="button" onClick={() => onChange(tags.filter((x: string) => x !== t))} className="ml-1 opacity-60 hover:opacity-100"><X className="h-3 w-3" /></button>
          </Badge>
        ))}
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === ",") { e.preventDefault(); if (input.trim()) { onChange([...tags, input.trim()]); setInput(""); } }
            if (e.key === "Backspace" && !input && tags.length) onChange(tags.slice(0, -1));
          }}
          placeholder={tags.length === 0 ? placeholder : ""}
          className="flex-1 min-w-[120px] bg-transparent outline-none text-sm px-1"
        />
      </div>
      <div className="text-xs text-[var(--muted-foreground)]">Press Enter or comma to add</div>
    </div>
  );
}

function GoalsTab() {
  const qc = useQueryClient();
  const { data: goals = [], isLoading } = useQuery({ queryKey: ["goals"], queryFn: async () => { try { const r = await goalsApi.list(); return extractList(r); } catch { return []; } } });
  const [showAdd, setShowAdd] = useState(false);
  const [filter, setFilter] = useState<"active" | "completed" | "all">("active");
  const filtered = goals.filter((g: any) => filter === "all" ? true : g.status === filter);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 p-1 rounded-full bg-[var(--muted)]">
          {(["active", "completed", "all"] as const).map((f) => (
            <button key={f} onClick={() => setFilter(f)} className={`px-4 py-1.5 rounded-full text-xs font-medium capitalize transition-all ${filter === f ? "bg-[var(--card)] shadow-sm" : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}>{f}</button>
          ))}
        </div>
        <Button variant="gradient" onClick={() => setShowAdd(true)}><Plus className="h-4 w-4" /> Add goal</Button>
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">{Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-48" />)}</div>
      ) : filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Target className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
            <p className="text-sm font-medium">No {filter} goals</p>
            <p className="text-xs text-[var(--muted-foreground)] mt-1">Set your first goal to get started!</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((g: any) => <GoalCard key={g.id} goal={g} onChanged={() => qc.invalidateQueries({ queryKey: ["goals"] })} />)}
        </div>
      )}

      {showAdd && <AddGoalDialog onClose={() => setShowAdd(false)} onSaved={() => { setShowAdd(false); qc.invalidateQueries({ queryKey: ["goals"] }); }} />}
    </div>
  );
}

function GoalCard({ goal: g, onChanged }: { goal: any; onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const pct = g.estimated_hours ? Math.min(100, Math.round((g.completed_hours / g.estimated_hours) * 100)) : 0;
  return (
    <Card className="hover:shadow-[var(--shadow-soft)] transition-all">
      <CardHeader>
        <CardTitle className="text-sm line-clamp-2">{g.title}</CardTitle>
        <div className="flex gap-1 flex-wrap mt-1">
          <Badge variant="default" className="capitalize text-[10px]">{g.category}</Badge>
          <Badge variant={g.priority === "high" ? "destructive" : g.priority === "medium" ? "warning" : "muted"} className="capitalize text-[10px]">{g.priority}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {g.estimated_hours && (
          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-[var(--muted-foreground)]">{g.completed_hours}/{g.estimated_hours} hrs</span>
              <span className="font-semibold tabular-nums">{pct}%</span>
            </div>
            <Progress value={pct} className={pct >= 100 ? "[&>div]:bg-emerald-500" : "[&>div]:bg-brand-500"} />
          </div>
        )}
        {g.target_date && <div className="text-xs text-[var(--muted-foreground)]">Due {new Date(g.target_date).toLocaleDateString()}</div>}
        {(g.milestones || []).length > 0 && (
          <button onClick={() => setExpanded(!expanded)} className="text-xs flex items-center gap-1 text-brand-500 hover:underline">
            {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />} {g.milestones.length} milestone{g.milestones.length !== 1 ? "s" : ""}
          </button>
        )}
        {expanded && (g.milestones || []).length > 0 && (
          <div className="space-y-1 pt-2 border-t border-[var(--border)]">
            {g.milestones.map((m: any, i: number) => (
              <div key={i} className={`text-xs ${m.completed ? "line-through text-emerald-500" : "text-[var(--muted-foreground)]"}`}>
                {m.completed ? "✓" : `${i + 1}.`} {m.title}
              </div>
            ))}
          </div>
        )}
        <div className="flex gap-1.5 pt-2">
          <Button size="sm" variant="outline" className="flex-1" onClick={() => toast.info("Log progress modal coming in Phase 7 polish")}><Clock className="h-3 w-3" /> Log hours</Button>
          <Button size="sm" variant="ghost" onClick={async () => {
            if (!confirm("Abandon this goal?")) return;
            try { await goalsApi.delete(g.id); toast.success("Goal abandoned"); onChanged(); } catch (err: any) { toast.error(err?.message || "Failed"); }
          }}><Trash2 className="h-3 w-3" /></Button>
        </div>
      </CardContent>
    </Card>
  );
}

function AddGoalDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [title, setTitle] = useState("");
  const [desc, setDesc] = useState("");
  const [category, setCategory] = useState("");
  const [priority, setPriority] = useState("medium");
  const [date, setDate] = useState("");
  const [est, setEst] = useState<number | "">("");
  const [milestones, setMilestones] = useState<{ title: string }[]>([]);
  const [saving, setSaving] = useState(false);

  async function save() {
    if (!title || !category) { toast.error("Title and category required"); return; }
    setSaving(true);
    try {
      await goalsApi.create({
        title, description: desc || undefined, category, priority,
        target_date: date || undefined,
        estimated_hours: est || undefined,
        milestones: milestones.filter((m) => m.title.trim()),
      });
      await dailyPlanApi.invalidateRoutine().catch(() => {});
      toast.success("Goal created!");
      onSaved();
    } catch (err: any) { toast.error(err?.message || "Failed"); }
    finally { setSaving(false); }
  }

  return (
    <div className="fixed inset-0 z-50 grid place-items-center bg-black/60 backdrop-blur-sm p-4 animate-[fadeIn_0.2s_ease-out]" onClick={onClose}>
      <Card className="w-full max-w-lg max-h-[90vh] overflow-y-auto animate-[scaleIn_0.2s_ease-out]" onClick={(e) => e.stopPropagation()}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Add new goal</CardTitle>
            <button onClick={onClose} className="h-7 w-7 rounded-md grid place-items-center text-[var(--muted-foreground)] hover:bg-[var(--accent)]"><X className="h-4 w-4" /></button>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2"><Label>Title *</Label><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Complete ML course on Coursera" /></div>
          <div className="space-y-2"><Label>Description</Label><Input value={desc} onChange={(e) => setDesc(e.target.value)} placeholder="Optional" /></div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2"><Label>Category *</Label>
              <select value={category} onChange={(e) => setCategory(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                <option value="">Select…</option>
                {["academic", "career", "skill", "project", "exam_prep"].map((c) => <option key={c} value={c} className="capitalize">{c.replace("_", " ")}</option>)}
              </select>
            </div>
            <div className="space-y-2"><Label>Priority</Label>
              <select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full h-10 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm">
                {["low", "medium", "high"].map((p) => <option key={p} value={p} className="capitalize">{p}</option>)}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-2"><Label>Target date</Label><Input type="date" value={date} onChange={(e) => setDate(e.target.value)} /></div>
            <div className="space-y-2"><Label>Estimated hours</Label><Input type="number" min={1} value={est} onChange={(e) => setEst(e.target.value ? parseInt(e.target.value) : "")} placeholder="40" /></div>
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between"><Label>Milestones</Label>
              <Button type="button" variant="ghost" size="sm" onClick={() => setMilestones([...milestones, { title: "" }])}><Plus className="h-3 w-3" /> Add</Button>
            </div>
            {milestones.map((m, i) => (
              <div key={i} className="flex gap-2">
                <Input value={m.title} onChange={(e) => setMilestones(milestones.map((mm, j) => j === i ? { title: e.target.value } : mm))} placeholder={`Milestone ${i + 1}`} />
                <Button variant="ghost" size="icon" onClick={() => setMilestones(milestones.filter((_, j) => j !== i))}><X className="h-3 w-3" /></Button>
              </div>
            ))}
          </div>
          <div className="flex gap-2 pt-2">
            <Button variant="gradient" onClick={save} disabled={saving} className="flex-1">{saving ? "Saving..." : "Create goal"}</Button>
            <Button variant="ghost" onClick={onClose}>Cancel</Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
