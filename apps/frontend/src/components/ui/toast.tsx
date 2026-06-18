import { Toaster as SonnerToaster } from "sonner";
import { useTheme } from "@/store/theme";

/**
 * Theme-aware Toaster. Reads the active theme from the theme store so
 * toasts always match the app shell. Render at the app root.
 */
export function Toaster(props: React.ComponentProps<typeof SonnerToaster>) {
  const theme = useTheme((s) => s.theme);
  return (
    <SonnerToaster
      theme={theme}
      position="bottom-right"
      richColors
      closeButton
      toastOptions={{
        classNames: {
          toast: "group toast group-[.toaster]:bg-[var(--card)] group-[.toaster]:text-[var(--card-foreground)] group-[.toaster]:border-[var(--border)] group-[.toaster]:shadow-[var(--shadow-elevated)]",
          description: "group-[.toast]:text-[var(--muted-foreground)]",
          actionButton: "group-[.toast]:bg-brand-500 group-[.toast]:text-white",
          cancelButton: "group-[.toast]:bg-[var(--muted)] group-[.toast]:text-[var(--muted-foreground)]",
        },
      }}
      {...props}
    />
  );
}

export { toast } from "sonner";
