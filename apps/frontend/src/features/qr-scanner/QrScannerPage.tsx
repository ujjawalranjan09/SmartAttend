import { useState, useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Camera, CameraOff, CheckCircle2, XCircle, ScanLine, Loader2, Keyboard, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import { attendanceApi, facesApi } from "@/lib/api";
import { PageHeader } from "@/components/common/PageHeader";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";

export function QrScannerPage() {
  const [status, setStatus] = useState<"idle" | "scanning" | "processing" | "success" | "error">("idle");
  const [message, setMessage] = useState("Camera idle");
  const [manualCode, setManualCode] = useState("");
  const containerId = "qr-reader-" + Math.random().toString(36).slice(2, 9);
  const scannerRef = useRef<any>(null);
  const mountedRef = useRef(false);

  const { data: faceStatus } = useQuery({
    queryKey: ["faces", "status"],
    queryFn: () => facesApi.status(),
    retry: 0,
    refetchOnWindowFocus: false,
  });
  const faceEnrolled = (faceStatus as any)?.enrolled;

  // Camera lifecycle — runs once. Uses a stable container element created imperatively
  // so html5-qrcode never tries to share DOM with React.
  useEffect(() => {
    mountedRef.current = true;
    let scanner: any = null;

    (async () => {
      try {
        // Load html5-qrcode library
        if (!(window as any).Html5Qrcode) {
          await new Promise<void>((resolve, reject) => {
            const s = document.createElement("script");
            s.src = "https://unpkg.com/html5-qrcode@2.3.8/html5-qrcode.min.js";
            s.onload = () => resolve();
            s.onerror = () => reject(new Error("Failed to load scanner library"));
            document.head.appendChild(s);
          });
        }
        if (!mountedRef.current) return;

        const { Html5Qrcode } = (window as any);

        // Create an isolated container imperatively — NOT owned by React
        const el = document.getElementById(containerId);
        if (!el) {
          setStatus("idle");
          setMessage("Scanner container not ready");
          return;
        }
        // Wipe any leftover children (HMR / re-mount safety)
        el.innerHTML = "";

        scanner = new Html5Qrcode(containerId, /* verbose */ false);
        scannerRef.current = scanner;

        await scanner.start(
          { facingMode: "environment" },
          { fps: 10, qrbox: { width: 240, height: 240 } },
          async (text: string) => {
            try { await scanner?.stop(); } catch {}
            handleCode(text);
          },
          () => {},
        );

        if (mountedRef.current) {
          setStatus("scanning");
          setMessage("Camera active — point at a QR code");
        }
      } catch (err: any) {
        if (mountedRef.current) {
          setStatus("idle");
          setMessage(err?.message?.includes("NotAllowed") ? "Camera permission denied. Allow access and reload." : "Camera unavailable — use manual entry below");
        }
      }
    })();

    return () => {
      mountedRef.current = false;
      try { scanner?.stop(); } catch {}
      try { scanner?.clear(); } catch {}
      scannerRef.current = null;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleCode(code: string) {
    setStatus("processing");
    setMessage("Submitting attendance…");
    let sessionId: string | null = null;
    let token = code;
    try {
      const url = new URL(code);
      sessionId = url.searchParams.get("session");
      token = url.searchParams.get("token") || code;
    } catch {
      // Not a URL — try as raw session ID
      const trimmed = code.trim();
      if (/^[0-9a-f]{8}-[0-9a-f]{4}-/i.test(trimmed)) sessionId = trimmed;
    }
    if (!sessionId) {
      setStatus("error");
      setMessage("Invalid QR code — could not extract session ID");
      return;
    }
    try {
      await attendanceApi.mark({ session_id: sessionId, qr_token: token });
      setStatus("success");
      setMessage("Attendance marked successfully!");
      toast.success("Attendance recorded!");
    } catch (err: any) {
      const msg = err?.response?.data?.detail || err?.message || "Failed to mark attendance";
      setStatus("error");
      setMessage(typeof msg === "string" ? msg : "Failed to mark attendance");
      toast.error(typeof msg === "string" ? msg : "Failed");
    }
  }

  return (
    <div className="space-y-6">
      <PageHeader title="Scan QR Code" description="Point your camera at the session QR to mark attendance" />

      <div className="max-w-xl mx-auto space-y-4">
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center gap-2"><ScanLine className="h-4 w-4" /> Camera</CardTitle>
                <CardDescription>{message}</CardDescription>
              </div>
              <StatusBadge status={status} />
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* html5-qrcode owns this DOM — React never touches it */}
            <div id={containerId} className="rounded-xl overflow-hidden bg-[var(--muted)] aspect-square max-w-sm mx-auto flex items-center justify-center" style={{ minHeight: 240 }}>
              {status === "idle" && <CameraOff className="h-12 w-12 text-[var(--muted-foreground)]" />}
            </div>

            <div className="relative flex items-center gap-3">
              <div className="h-px flex-1 bg-[var(--border)]" />
              <span className="text-xs uppercase tracking-wider text-[var(--muted-foreground)] flex items-center gap-1.5"><Keyboard className="h-3 w-3" /> or enter manually</span>
              <div className="h-px flex-1 bg-[var(--border)]" />
            </div>

            <form onSubmit={(e) => { e.preventDefault(); if (manualCode.trim()) handleCode(manualCode.trim()); }} className="flex gap-2">
              <Input value={manualCode} onChange={(e) => setManualCode(e.target.value)} placeholder="Paste QR code or session URL" />
              <Button type="submit" variant="gradient" disabled={!manualCode.trim() || status === "processing"}>
                {status === "processing" ? <Loader2 className="h-4 w-4 animate-spin" /> : "Submit"}
              </Button>
            </form>

            {status === "success" && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-5 w-5" />
                <span className="text-sm font-medium">You're checked in</span>
              </div>
            )}
            {status === "error" && (
              <div className="flex items-center gap-2 p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400">
                <XCircle className="h-5 w-5" />
                <span className="text-sm">{message}</span>
              </div>
            )}
          </CardContent>
        </Card>

        {faceEnrolled && (
          <Card>
            <CardContent className="pt-6 text-center">
              <div className="text-sm text-[var(--muted-foreground)]">Face verification enabled — your face will verify attendance after QR scan.</div>
            </CardContent>
          </Card>
        )}

        {!faceEnrolled && status !== "error" && (
          <Card>
            <CardContent className="pt-6 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-amber-500 shrink-0 mt-0.5" />
              <div className="text-sm text-[var(--muted-foreground)]">
                <strong className="text-amber-600 dark:text-amber-400">Tip:</strong> enroll your face in Settings → Face recognition for biometric verification.
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { variant: any; label: string }> = {
    idle: { variant: "muted", label: "Idle" },
    scanning: { variant: "success", label: "Scanning" },
    processing: { variant: "warning", label: "Processing" },
    success: { variant: "success", label: "Success" },
    error: { variant: "destructive", label: "Error" },
  };
  const m = map[status] || map.idle;
  return <Badge variant={m.variant}>{m.label}</Badge>;
}
