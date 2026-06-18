import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { Eye, EyeOff, Loader2, Sparkles, Shield, Zap, Users } from "lucide-react";
import { toast } from "sonner";
import { authApi, setToken } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Logo } from "@/components/common/Logo";

const DEMO_ACCOUNTS = [
  { label: "Admin", email: "admin@smartattend.in", password: "Admin@1234", color: "from-purple-500 to-pink-500", emoji: "👑" },
  { label: "Faculty", email: "faculty@smartattend.in", password: "Faculty@1234", color: "from-brand-500 to-brand-700", emoji: "👨‍🏫" },
  { label: "Student", email: "student1@smartattend.in", password: "Student@1234", color: "from-emerald-500 to-teal-500", emoji: "🎓" },
];

export function LoginPage() {
  const navigate = useNavigate();
  const setUser = useAuth((s) => s.setUser);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const { access_token } = await authApi.login(email, password);
      setToken(access_token);
      const me = await authApi.me();
      setUser(me as any);
      toast.success(`Welcome back, ${me.full_name?.split(" ")[0] || "there"}!`);
      navigate("/dashboard", { replace: true });
    } catch (err: any) {
      setError(err?.status === 429 ? "Too many attempts. Wait a minute and try again." : err?.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  }

  function useDemo(acct: typeof DEMO_ACCOUNTS[number]) {
    setEmail(acct.email);
    setPassword(acct.password);
  }

  return (
    <div className="min-h-dvh grid lg:grid-cols-2">
      {/* Left: form */}
      <div className="flex items-center justify-center p-6 lg:p-12 bg-[var(--background)]">
        <div className="w-full max-w-md animate-[fadeIn_0.4s_ease-out]">
          <div className="mb-10">
            <Logo size="lg" withWordmark className="[&_span]:text-xl" />
          </div>

          <div className="space-y-2 mb-8">
            <h1 className="text-3xl font-bold tracking-tight">Welcome back</h1>
            <p className="text-[var(--muted-foreground)]">Sign in to continue to your dashboard.</p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                placeholder="you@smartattend.in"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
              />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password">Password</Label>
                <Link to="/forgot-password" className="text-xs text-brand-500 hover:underline">Forgot password?</Link>
              </div>
              <div className="relative">
                <Input
                  id="password"
                  type={showPw ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                  required
                  className="pr-10"
                />
                <button
                  type="button"
                  onClick={() => setShowPw(!showPw)}
                  className="absolute right-2 top-1/2 -translate-y-1/2 h-7 w-7 rounded-md flex items-center justify-center text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
                  aria-label={showPw ? "Hide password" : "Show password"}
                >
                  {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            {error && (
              <div className="rounded-md bg-[var(--error)]/10 border border-[var(--error)]/30 text-[var(--error)] text-sm px-3 py-2 animate-[slideUp_0.2s_ease-out]" role="alert">
                {error}
              </div>
            )}

            <Button type="submit" disabled={loading} className="w-full" size="lg" variant="gradient">
              {loading && <Loader2 className="h-4 w-4 animate-spin" />}
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </form>

          {import.meta.env.DEV && (
            <div className="mt-8 pt-6 border-t border-[var(--border)]">
              <p className="text-xs uppercase tracking-wider text-[var(--muted-foreground)] text-center mb-3">
                Quick demo accounts
              </p>
              <div className="grid grid-cols-3 gap-2">
                {DEMO_ACCOUNTS.map((a) => (
                  <button
                    type="button"
                    key={a.email}
                    onClick={() => useDemo(a)}
                    className="group relative rounded-lg border border-[var(--border)] bg-[var(--card)] p-3 text-xs hover:border-brand-500 hover:shadow-sm transition-all"
                  >
                    <div className={`text-lg mb-1 bg-gradient-to-br ${a.color} bg-clip-text text-transparent font-bold`}>
                      {a.emoji} {a.label}
                    </div>
                    <div className="text-[10px] text-[var(--muted-foreground)] truncate">{a.email}</div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Right: hero */}
      <div className="hidden lg:flex relative overflow-hidden bg-gradient-to-br from-brand-700 via-brand-600 to-brand-800 p-12">
        <div className="absolute inset-0 bg-mesh opacity-40" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(255,255,255,0.15),transparent_60%)]" />

        <div className="relative z-10 flex flex-col justify-between text-white w-full">
          <div className="space-y-4 max-w-md">
            <div className="inline-flex items-center gap-2 rounded-full bg-white/10 backdrop-blur-sm border border-white/20 px-3 py-1 text-xs">
              <Sparkles className="h-3 w-3" />
              AI-augmented attendance
            </div>
            <h2 className="text-4xl xl:text-5xl font-bold tracking-tight leading-tight">
              Mark attendance in seconds. <span className="text-brand-200">Catch proxies</span> before they happen.
            </h2>
            <p className="text-brand-100 text-lg">
              QR rotation, face verification, and ML-powered insights — all in one platform built for universities.
            </p>
          </div>

          <div className="grid grid-cols-3 gap-3 mt-12">
            {[
              { icon: Zap, label: "QR + Face", desc: "Verify in <2s" },
              { icon: Shield, label: "Proxy shield", desc: "ML risk scoring" },
              { icon: Users, label: "Multi-role", desc: "Admin · Faculty · Student" },
            ].map(({ icon: Icon, label, desc }) => (
              <div key={label} className="rounded-xl bg-white/10 backdrop-blur-sm border border-white/20 p-4 hover:bg-white/15 transition-colors">
                <Icon className="h-5 w-5 mb-2" />
                <div className="text-sm font-semibold">{label}</div>
                <div className="text-xs text-brand-100">{desc}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
