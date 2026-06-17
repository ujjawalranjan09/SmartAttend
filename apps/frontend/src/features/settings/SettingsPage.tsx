import { useEffect, useRef, useState } from "react";
import { Save, Lock, Shield, Bell, Palette, Camera, Trash2, User as UserIcon, Moon, Sun, X, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { authApi, facesApi } from "@/lib/api";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";
import { initials } from "@/lib/utils";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";

export function SettingsPage() {
  const { user, setUser } = useAuth();
  const { theme, toggle } = useTheme();
  const [name, setName] = useState(user?.full_name || "");
  const [phone, setPhone] = useState(user?.phone || "");
  const [saving, setSaving] = useState(false);

  async function saveProfile(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      await authApi.updateProfile({ full_name: name, phone });
      setUser({ ...user!, full_name: name, phone });
      toast.success("Profile updated");
    } catch (err: any) {
      toast.error(err?.message || "Failed to update");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Settings" description="Manage your account and preferences" />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Profile</CardTitle><CardDescription>Your personal information</CardDescription></CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 mb-6 pb-6 border-b border-[var(--border)]">
              <div className="h-16 w-16 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white text-xl font-bold">
                {initials(user?.full_name)}
              </div>
              <div>
                <div className="font-semibold">{user?.full_name || "—"}</div>
                <div className="text-sm text-[var(--muted-foreground)]">{user?.email}</div>
                <Badge variant="default" className="mt-1 capitalize">{user?.role}</Badge>
              </div>
            </div>
            <form onSubmit={saveProfile} className="space-y-4">
              <div className="space-y-2"><Label htmlFor="s-name">Full name</Label><Input id="s-name" value={name} onChange={(e) => setName(e.target.value)} /></div>
              <div className="space-y-2"><Label htmlFor="s-email">Email</Label><Input id="s-email" value={user?.email || ""} disabled /></div>
              <div className="space-y-2"><Label htmlFor="s-phone">Phone</Label><Input id="s-phone" type="tel" placeholder="+91 XXXXXXXXXX" value={phone} onChange={(e) => setPhone(e.target.value)} /></div>
              <Button type="submit" variant="gradient" disabled={saving}><Save className="h-4 w-4" /> {saving ? "Saving..." : "Save changes"}</Button>
            </form>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle>Security</CardTitle></CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" onClick={() => toast.info("Password reset email sent (demo)")}><Lock className="h-4 w-4" /> Change password</Button>
              <Button variant="outline" className="w-full justify-start" onClick={() => toast.info("2FA setup coming soon")}><Shield className="h-4 w-4" /> Enable 2FA (TOTP)</Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Notifications</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              {[
                ["Low attendance alerts", true],
                ["Session start reminders", true],
                ["Weekly report emails", false],
                ["Push notifications", true],
              ].map(([label, def]) => (
                <label key={label as string} className="flex items-center justify-between cursor-pointer">
                  <span className="text-sm">{label}</span>
                  <input type="checkbox" defaultChecked={def as boolean} className="h-4 w-4 rounded border-[var(--border)] accent-brand-500" />
                </label>
              ))}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle>Appearance</CardTitle></CardHeader>
            <CardContent>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
                  <span className="text-sm">Theme</span>
                </div>
                <Button variant="outline" size="sm" onClick={toggle}>{theme === "dark" ? "Switch to light" : "Switch to dark"}</Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {user?.role === "student" && <FaceEnrollmentCard />}
    </div>
  );
}

function FaceEnrollmentCard() {
  const [status, setStatus] = useState<"loading" | "enrolled" | "not-enrolled" | "error">("loading");
  const [enrolledAt, setEnrolledAt] = useState<string | null>(null);
  const [capturing, setCapturing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  async function refresh() {
    try {
      const s: { enrolled?: boolean; enrolled_at?: string | null } = await facesApi.status();
      setStatus(s.enrolled ? "enrolled" : "not-enrolled");
      setEnrolledAt(s.enrolled_at || null);
    } catch {
      setStatus("error");
    }
  }

  function stopStream() {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480 },
      });
      streamRef.current = stream;
      setCapturing(true);
      // Attach stream after the <video> element has been mounted this render.
      requestAnimationFrame(() => {
        const v = videoRef.current;
        if (v && streamRef.current) {
          v.srcObject = streamRef.current;
          v.play().catch(() => { /* autoplay may be blocked; user can still capture */ });
        }
      });
    } catch {
      toast.error("Camera access denied. Please grant permission in your browser.");
    }
  }

  function cancelCapture() {
    stopStream();
    setCapturing(false);
  }

  async function capturePhoto() {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const width = video.videoWidth || 640;
    const height = video.videoHeight || 480;
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext("2d");
    if (!ctx) {
      toast.error("Failed to initialise capture canvas");
      return;
    }
    ctx.drawImage(video, 0, 0, width, height);

    const blob: Blob | null = await new Promise((resolve) =>
      canvas.toBlob((b) => resolve(b), "image/jpeg", 0.85),
    );
    if (!blob) {
      toast.error("Failed to capture image");
      return;
    }

    setSubmitting(true);
    try {
      await facesApi.enroll(blob);
      toast.success("Face enrolled successfully");
      stopStream();
      setCapturing(false);
      await refresh();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Face enrollment failed";
      toast.error(msg);
    } finally {
      setSubmitting(false);
    }
  }

  // Ensure the camera stream is released if the component unmounts mid-capture.
  useEffect(() => {
    return () => {
      stopStream();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (status === "loading") {
    return (
      <Card>
        <CardHeader><CardTitle>Face recognition</CardTitle></CardHeader>
        <CardContent><p className="text-sm text-[var(--muted-foreground)]">Loading enrollment status…</p></CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2"><Camera className="h-4 w-4" /> Face recognition</CardTitle>
            <CardDescription>Enroll your face for biometric attendance verification</CardDescription>
          </div>
          {status === "enrolled" ? <Badge variant="success">Enrolled</Badge> : <Badge variant="muted">Not enrolled</Badge>}
        </div>
      </CardHeader>
      <CardContent>
        {status === "enrolled" ? (
          <div className="flex items-center justify-between p-4 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-full bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 flex items-center justify-center shrink-0">
                <CheckCircle2 className="h-5 w-5" />
              </div>
              <div>
                <div className="font-medium text-sm">Face enrolled{enrolledAt ? ` on ${new Date(enrolledAt).toLocaleDateString()}` : ""}</div>
                <div className="text-xs text-[var(--muted-foreground)] mt-0.5">Your face will be used to verify attendance during QR scans.</div>
              </div>
            </div>
            <Button variant="destructive" size="sm" onClick={async () => {
              if (!confirm("Remove face enrollment? This cannot be undone.")) return;
              try { await facesApi.delete(); toast.success("Enrollment removed"); refresh(); }
              catch { toast.error("Failed to remove"); }
            }}><Trash2 className="h-3 w-3" /> Remove</Button>
          </div>
        ) : capturing ? (
          <div className="space-y-4">
            <div className="flex flex-col items-center gap-3">
              <div className="relative h-[200px] w-[200px] rounded-full overflow-hidden border-2 border-brand-500 bg-black shadow-[0_0_0_4px_rgba(var(--brand-500-rgb,99_102_241),0.15)]">
                <video
                  ref={videoRef}
                  autoPlay
                  playsInline
                  muted
                  className="h-full w-full object-cover"
                />
              </div>
              <p className="text-sm text-[var(--muted-foreground)] text-center max-w-xs">
                Position your face inside the circle and hold still, then click Capture.
              </p>
            </div>
            <canvas ref={canvasRef} className="hidden" aria-hidden="true" />
            <div className="flex items-center justify-center gap-2">
              <Button variant="outline" onClick={cancelCapture} disabled={submitting}>
                <X className="h-4 w-4" /> Cancel
              </Button>
              <Button variant="gradient" onClick={capturePhoto} disabled={submitting}>
                <Camera className="h-4 w-4" /> {submitting ? "Uploading…" : "Capture Photo"}
              </Button>
            </div>
          </div>
        ) : (
          <div className="text-center py-6">
            <div className="h-16 w-16 rounded-full bg-brand-500/10 text-brand-500 flex items-center justify-center mx-auto mb-3">
              <Camera className="h-7 w-7" />
            </div>
            <p className="text-sm text-[var(--muted-foreground)] mb-3">Enroll your face so the system can verify it's really you.</p>
            <Button variant="gradient" onClick={startCamera}>
              <Camera className="h-4 w-4" /> Capture Photo
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
