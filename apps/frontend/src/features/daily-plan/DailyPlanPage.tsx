import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, ChevronRight, Sparkles, Calendar, RefreshCw, BookOpen, Coffee, Brain, Target, Lightbulb, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import { dailyPlanApi } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";

function today() { return new Date().toISOString().split("T")[0]; }
function label(d: string) {
  const date = new Date(d + "T00:00:00");
  const diff = Math.round((date.getTime() - new Date().setHours(0,0,0,0)) / 86400000);
  if (diff === 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff === -1) return "Yesterday";
  return date.toLocaleDateString("en-IN", { weekday: "long", month: "short", day: "numeric" });
}

export function DailyPlanPage() {
  const [date, setDate] = useState(today());
  const [tab, setTab] = useState<"free" | "routine">("free");

  return (
    <div className="space-y-6">
      <PageHeader title="My Day" description="Free periods, study suggestions, and your daily routine" />

      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center gap-2 flex-wrap">
            <Button variant="outline" size="icon" onClick={() => { const d = new Date(date); d.setDate(d.getDate() - 1); setDate(d.toISOString().split("T")[0]); }}>
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="h-9 rounded-md border border-[var(--border)] bg-[var(--background)] px-3 text-sm" />
            <Button variant="outline" size="icon" onClick={() => { const d = new Date(date); d.setDate(d.getDate() + 1); setDate(d.toISOString().split("T")[0]); }}>
              <ChevronRight className="h-4 w-4" />
            </Button>
            <div className="text-sm font-medium ml-2">{label(date)}</div>
          </div>
        </CardContent>
      </Card>

      <div className="flex gap-1 border-b border-[var(--border)]">
        {([["free", "Free Periods"], ["routine", "AI Routine"]] as const).map(([id, l]) => (
          <button key={id} onClick={() => setTab(id as any)} className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors flex items-center gap-1.5 ${tab === id ? "border-brand-500 text-brand-500" : "border-transparent text-[var(--muted-foreground)] hover:text-[var(--foreground)]"}`}>
            {id === "routine" && <Sparkles className="h-3.5 w-3.5" />}
            {l}
          </button>
        ))}
      </div>

      {tab === "free" ? <FreePeriods date={date} /> : <RoutineView date={date} />}
    </div>
  );
}

function FreePeriods({ date }: { date: string }) {
  const { data, isLoading } = useQuery({ queryKey: ["free-periods", date], queryFn: () => dailyPlanApi.getFreePeriods(date), retry: 0 });
  if (isLoading) return <Skeleton className="h-64" />;
  if (!data || (!((data as any).classes?.length) && !((data as any).free_periods?.length))) {
    return (
      <Card><CardContent className="py-12 text-center">
        <Calendar className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
        <p className="font-medium">No schedule data</p>
        <p className="text-sm text-[var(--muted-foreground)] mt-1">You have no classes or free periods for this day.</p>
      </CardContent></Card>
    );
  }

  const blocks: any[] = [];
  ((data as any).classes || []).forEach((c: any) => blocks.push({ type: "class", start: c.start_time, end: c.end_time, data: c }));
  ((data as any).free_periods || []).forEach((fp: any) => blocks.push({ type: "free", start: fp.start_time, end: fp.end_time, duration: fp.duration_minutes, suggestions: fp.suggestions || [] }));
  blocks.sort((a, b) => a.start.localeCompare(b.start));

  return (
    <div className="space-y-2">
      {blocks.map((b, i) => b.type === "class" ? (
        <Card key={i} className="border-l-4 border-l-brand-500">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="text-xs font-mono tabular-nums text-[var(--muted-foreground)] pt-1 w-24 shrink-0">{b.start} – {b.end}</div>
              <div className="flex-1">
                <Badge variant="default" className="mb-1">Class</Badge>
                <div className="font-semibold">{b.data.course_name}</div>
                {b.data.room && <div className="text-sm text-[var(--muted-foreground)]">{b.data.room}</div>}
              </div>
            </div>
          </CardContent>
        </Card>
      ) : (
        <Card key={i} className="border-l-4 border-l-emerald-500">
          <CardContent className="pt-6">
            <div className="flex items-start gap-4">
              <div className="text-xs font-mono tabular-nums text-[var(--muted-foreground)] pt-1 w-24 shrink-0">{b.start} – {b.end}<div className="text-[10px]">({b.duration} min)</div></div>
              <div className="flex-1 space-y-2">
                <Badge variant="success">Free Period</Badge>
                {b.suggestions.length > 0 ? (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-2">
                    {b.suggestions.map((s: any, j: number) => (
                      <div key={j} className="rounded-lg border border-[var(--border)] bg-[var(--muted)] p-3 hover:border-brand-500/50 transition-colors">
                        <div className="flex items-start justify-between gap-2 mb-1">
                          <div className="font-medium text-sm">{s.title}</div>
                          <Badge variant="muted" className="text-[10px]">{s.duration_minutes}m</Badge>
                        </div>
                        <div className="text-xs text-[var(--muted-foreground)] line-clamp-2">{s.description}</div>
                        {s.goal_id && <div className="text-[10px] text-brand-500 mt-1 flex items-center gap-1"><Target className="h-2.5 w-2.5" /> Linked goal</div>}
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-[var(--muted-foreground)]">No suggestions. Complete your profile for personalized ideas.</p>
                )}
              </div>
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function RoutineView({ date }: { date: string }) {
  const { data, isLoading, refetch } = useQuery({ queryKey: ["routine", date], queryFn: () => dailyPlanApi.getRoutine(date), retry: 0 });

  if (isLoading) return <div className="space-y-2"><Skeleton className="h-24" /><Skeleton className="h-64" /></div>;
  if (!data || !(data as any).routine?.length) {
    return <Card><CardContent className="py-12 text-center">
      <Sparkles className="h-12 w-12 mx-auto text-[var(--muted-foreground)] mb-3" />
      <p className="font-medium">No routine yet</p>
      <p className="text-sm text-[var(--muted-foreground)] mt-1">No classes scheduled for this day.</p>
    </CardContent></Card>;
  }

  const summary = (data as any).summary || {};
  const genBy = (data as any).generated_by;
  const blocks = (data as any).routine;

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2"><Sparkles className="h-4 w-4 text-brand-500" /> Plan summary</CardTitle>
            <Button variant="outline" size="sm" onClick={async () => { await dailyPlanApi.invalidateRoutine().catch(() => {}); refetch(); toast.success("Regenerating..."); }}>
              <RefreshCw className="h-3 w-3" /> Regenerate
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {[
              { label: "Classes", val: summary.total_classes ?? blocks.filter((b: any) => b.type === "class").length, icon: BookOpen, color: "text-brand-500" },
              { label: "Study hrs", val: summary.total_study_hours ?? "—", icon: Brain, color: "text-emerald-500" },
              { label: "Break hrs", val: summary.total_break_hours ?? "—", icon: Coffee, color: "text-amber-500" },
              { label: "Free hrs", val: summary.total_free_hours ?? "—", icon: Calendar, color: "text-blue-500" },
            ].map(({ label, val, icon: Icon, color }) => (
              <div key={label} className="rounded-lg bg-[var(--muted)] p-3 text-center">
                <Icon className={`h-4 w-4 mx-auto mb-1 ${color}`} />
                <div className="text-2xl font-bold tabular-nums">{val}</div>
                <div className="text-[10px] uppercase tracking-wider text-[var(--muted-foreground)] mt-0.5">{label}</div>
              </div>
            ))}
          </div>
          {summary.daily_tip && (
            <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/20">
              <Lightbulb className="h-4 w-4 text-amber-500 mt-0.5 shrink-0" />
              <div className="text-sm">{summary.daily_tip}</div>
            </div>
          )}
          {genBy === "fallback" && (
            <div className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400"><AlertCircle className="h-3 w-3" /> Basic plan — AI planner unavailable</div>
          )}
          {genBy === "cached" && (
            <div className="flex items-center gap-2 text-xs text-brand-500"><Sparkles className="h-3 w-3" /> Cached result</div>
          )}
        </CardContent>
      </Card>

      <div className="space-y-2">
        {blocks.map((b: any, i: number) => {
          const styles: Record<string, any> = {
            class: { border: "border-l-brand-500", badge: <Badge variant="default">Class</Badge> },
            study: { border: "border-l-emerald-500", badge: <Badge variant="success">Study</Badge> },
            break: { border: "border-l-amber-500", badge: <Badge variant="warning">Break</Badge> },
            free: { border: "border-l-neutral-400", badge: <Badge variant="muted">Free</Badge> },
          };
          const s = styles[b.type] || styles.free;
          return (
            <Card key={i} className={`border-l-4 ${s.border}`}>
              <CardContent className="pt-6">
                <div className="flex items-start gap-4">
                  <div className="text-xs font-mono tabular-nums text-[var(--muted-foreground)] pt-1 w-24 shrink-0">{b.start} – {b.end}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-1.5 mb-1">{s.badge}</div>
                    <div className="font-semibold">{b.course_name || b.title || b.type}</div>
                    {b.description && <div className="text-sm text-[var(--muted-foreground)] mt-1">{b.description}</div>}
                    {b.goal_title && <div className="text-xs text-brand-500 mt-1 flex items-center gap-1"><Target className="h-3 w-3" /> {b.goal_title}</div>}
                  </div>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
