import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2, Mail } from "lucide-react";
import { toast } from "sonner";
import { authApi } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await authApi.forgotPassword(email);
      setDone(true);
      toast.success("Reset link sent! Check your email.");
    } catch (err: any) {
      toast.error(err?.message || "Failed to send reset link");
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
            <Mail className="h-6 w-6" />
          </div>

          {done ? (
            <div className="space-y-4 animate-[fadeIn_0.3s_ease-out]">
              <h1 className="text-2xl font-bold tracking-tight">Check your inbox</h1>
              <p className="text-[var(--muted-foreground)]">
                We've sent a password reset link to <strong className="text-[var(--foreground)]">{email}</strong>. Click the link to set a new password.
              </p>
              <p className="text-sm text-[var(--muted-foreground)]">
                Didn't get it? Check your spam folder or{" "}
                <button onClick={() => setDone(false)} className="text-brand-500 hover:underline">
                  try another email
                </button>
                .
              </p>
            </div>
          ) : (
            <>
              <h1 className="text-2xl font-bold tracking-tight mb-2">Forgot password?</h1>
              <p className="text-[var(--muted-foreground)] mb-6">
                No worries. Enter your email and we'll send you a reset link.
              </p>
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
                <Button type="submit" disabled={loading} className="w-full" size="lg" variant="gradient">
                  {loading && <Loader2 className="h-4 w-4 animate-spin" />}
                  Send reset link
                </Button>
              </form>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
