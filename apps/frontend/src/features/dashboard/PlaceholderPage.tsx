import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Sparkles } from "lucide-react";

interface PlaceholderPageProps {
  title: string;
  description?: string;
  emoji?: string;
}

export function PlaceholderPage({ title, description, emoji = "🚧" }: PlaceholderPageProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          {description && <p className="text-[var(--muted-foreground)] mt-1">{description}</p>}
        </div>
      </div>
      <Card className="overflow-hidden">
        <div className="h-1 bg-gradient-to-r from-brand-400 via-brand-500 to-brand-600" />
        <CardHeader>
          <div className="flex items-center gap-3">
            <span className="text-3xl">{emoji}</span>
            <div>
              <CardTitle>Coming in Phase 3+</CardTitle>
              <CardDescription className="flex items-center gap-1 mt-1">
                <Sparkles className="h-3 w-3" />
                Polished interactive UI ships after the foundation lands
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="text-sm text-[var(--muted-foreground)]">
          The shell, routing, auth, theme, and design system are live. Individual pages get filled in next.
        </CardContent>
      </Card>
    </div>
  );
}
