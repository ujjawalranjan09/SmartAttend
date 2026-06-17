import { useState } from "react";
import { useNavigate, useSearchParams, Link } from "react-router-dom";
import { ArrowLeft, Loader2, Lock, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) { setError("Passwords do not match"); return; }
    if (password.length < 8) { setError("Password must be at least 8 characters"); return; }
    setLoading(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
      toast.success("Password reset successful!");
      setTimeout(() => navigate("/login", { replace: true }), 1500);
    } catch (err: any) {
      setError(err?.message || "Failed to reset password");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-dvh flex items-center justify-center p-6 bg-mesh">
      <div className="w-full max-w-md animate-[fadeIn_0.4s_ease-out]">
        <Link to="/login" className="inline-flex items-center gap-2 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] mb-6 transition-colors">
          <ArrowLeft className="h-4 w-4" /> Back to sign in
        </Link>

        <div className="rounded-2xl border border-[var(--border)] bg-[var(--card)] p-8 shadow-[var(--shadow-elevated)]">
          <div className="h-12 w-12 rounded-xl bg-brand-500/10 text-brand-500 flex items-center justify-center mb-6">
            <Lock className="h-6 w-6" />
          </div>

          {done ? (
            <div className="text-center space-y-3 animate-[fadeIn_0.3s_ease-out]">
              <CheckCircle2 className="h-12 w-12 text-emerald-500 mx-auto" />
              <h1 className="text-2xl font-bold tracking-tight">Password reset!</h1>
              <p className="text-[var(--muted-foreground)]">Redirecting you to sign in...</p>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold tracking-tight mb-2">Set new password</h1>
              <p className="text-[var(--muted-foreground)] mb-6">Choose a strong password you don't reuse.</p>
              <form onSubmit={handleSubmit} className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="password">New password</Label>
                  <Input id="password" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={8} />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm">Confirm password</Label>
                  <Input id="confirm" type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} required minLength={8} />
                </div>
                {error && <div className="rounded-md bg-red-500/10 border border-red-500/30 text-red-600 text-sm px-3 py-2">{error}</div>}
                <Button type="submit" disabled={loading} className="w-full" size="lg" variant="gradient">
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Reset password
                </Button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
