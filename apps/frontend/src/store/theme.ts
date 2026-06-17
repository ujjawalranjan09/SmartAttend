import { create } from "zustand";

export type Theme = "light" | "dark";

interface ThemeState {
  theme: Theme;
  setTheme: (t: Theme) => void;
  toggle: () => void;
}

function applyTheme(theme: Theme) {
  if (typeof document === "undefined") return;
  const root = document.documentElement;
  root.classList.toggle("dark", theme === "dark");
  root.classList.toggle("light", theme === "light");
  root.style.colorScheme = theme;
}

const stored = (typeof localStorage !== "undefined" ? localStorage.getItem("smartattend_theme") : null) as Theme | null;
const initial: Theme = stored === "light" || stored === "dark" ? stored : "dark";

export const useTheme = create<ThemeState>((set, get) => ({
  theme: initial,
  setTheme: (t) => {
    localStorage.setItem("smartattend_theme", t);
    applyTheme(t);
    set({ theme: t });
  },
  toggle: () => {
    const next = get().theme === "dark" ? "light" : "dark";
    localStorage.setItem("smartattend_theme", next);
    applyTheme(next);
    set({ theme: next });
  },
}));

// Apply on boot
if (typeof window !== "undefined") applyTheme(initial);
