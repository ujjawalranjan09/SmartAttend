import { useLocation, useNavigate } from "react-router-dom";
import { Menu, Bell, Search, Command, LogOut, User as UserIcon, Settings as SettingsIcon, Sun, Moon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { NAV } from "@/lib/nav";
import { useAuth } from "@/store/auth";
import { useTheme } from "@/store/theme";
import { useQuery } from "@tanstack/react-query";
import { authApi, notificationsApi, setToken } from "@/lib/api";
import { toast } from "sonner";
import { useState, useEffect, useRef } from "react";
import { cn, initials } from "@/lib/utils";

interface TopbarProps {
  onMobileMenu: () => void;
}

export function Topbar({ onMobileMenu }: TopbarProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const role = user?.role || "student";
  const { theme, toggle: toggleTheme } = useTheme();
  const [openNotif, setOpenNotif] = useState(false);
  const [openUser, setOpenUser] = useState(false);
  const userRef = useRef<HTMLDivElement>(null);
  const notifRef = useRef<HTMLDivElement>(null);

  const navItem = NAV[role]?.flatMap((s) => s.items || []).find((i) => i.id === location.pathname.slice(1));

  const { data: notifs } = useQuery({
    queryKey: ["notifications"],
    queryFn: () => notificationsApi.list({ limit: 20 }),
    refetchInterval: 30_000,
    enabled: !!user,
  });
  const items = (notifs as any)?.items || (notifs as any) || [];
  const unread = items.filter((n: any) => !n.is_read).length;

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (userRef.current && !userRef.current.contains(e.target as Node)) setOpenUser(false);
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) setOpenNotif(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  async function handleLogout() {
    try { await authApi.logout(); } catch {}
    setToken(null);
    logout();
    toast.success("Signed out");
    navigate("/login", { replace: true });
  }

  return (
    <header className="h-16 sticky top-0 z-30 flex items-center gap-2 px-4 lg:px-6 bg-[var(--background)]/80 backdrop-blur-md border-b border-[var(--border)]">
      <Button variant="ghost" size="icon" onClick={onMobileMenu} className="lg:hidden" aria-label="Open menu">
        <Menu className="h-5 w-5" />
      </Button>

      <div className="flex items-center gap-2 min-w-0 flex-1">
        <h1 className="text-base font-semibold truncate">{navItem?.label || "Dashboard"}</h1>
      </div>

      <div className="hidden md:flex items-center gap-1 px-3 h-9 rounded-lg border border-[var(--border)] bg-[var(--card)] text-sm text-[var(--muted-foreground)] min-w-[200px] cursor-text hover:border-[var(--muted-foreground)]/40 transition-colors" role="search" aria-label="Search">
        <Search className="h-3.5 w-3.5" />
        <span className="text-xs flex-1">Search...</span>
        <kbd className="hidden sm:inline-flex items-center gap-0.5 text-[10px] font-mono bg-[var(--muted)] px-1.5 h-5 rounded">
          <Command className="h-2.5 w-2.5" /> K
        </kbd>
      </div>

      <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
        {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
      </Button>

      <div ref={notifRef} className="relative">
        <Button variant="ghost" size="icon" onClick={() => setOpenNotif((o) => !o)} aria-label="Notifications" className="relative">
          <Bell className="h-4 w-4" />
          {unread > 0 && (
            <span className="absolute top-1.5 right-1.5 h-2 w-2 rounded-full bg-[var(--error)] ring-2 ring-[var(--background)] animate-pulse" />
          )}
        </Button>
        {openNotif && (
          <div className="absolute right-0 top-12 w-80 sm:w-96 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-elevated)] z-50 overflow-hidden animate-[slideUp_0.2s_ease-out]" role="menu">
            <div className="px-4 py-3 flex items-center justify-between border-b border-[var(--border)]">
              <h3 className="font-semibold">Notifications</h3>
              {unread > 0 && <span className="text-xs text-brand-500">{unread} new</span>}
            </div>
            <div className="max-h-[400px] overflow-y-auto">
              {items.length === 0 ? (
                <div className="py-12 text-center text-sm text-[var(--muted-foreground)]">No notifications yet</div>
              ) : (
                items.map((n: any) => (
                  <div
                    key={n.id}
                    className={cn(
                      "px-4 py-3 border-b border-[var(--border)] last:border-0 hover:bg-[var(--accent)] cursor-pointer transition-colors",
                      !n.is_read && "bg-brand-500/5"
                    )}
                    onClick={async () => {
                      try { await notificationsApi.markRead(n.id); } catch {}
                      setOpenNotif(false);
                    }}
                  >
                    <div className="flex gap-3">
                      {!n.is_read && <span className="mt-1.5 h-2 w-2 rounded-full bg-brand-500 shrink-0" />}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium">{n.title || "Notification"}</p>
                        {n.body && <p className="text-xs text-[var(--muted-foreground)] line-clamp-2 mt-0.5">{n.body}</p>}
                        <p className="text-[10px] text-[var(--muted-foreground)] mt-1">{new Date(n.created_at).toLocaleString("en-IN")}</p>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}
      </div>

      <div ref={userRef} className="relative">
        <button
          onClick={() => setOpenUser((o) => !o)}
          className="flex items-center gap-2 h-9 pl-1 pr-2 rounded-lg hover:bg-[var(--accent)] transition-colors"
          aria-label="User menu"
          aria-expanded={openUser}
        >
          <div className="h-7 w-7 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white text-xs font-semibold">
            {initials(user?.full_name)}
          </div>
          <span className="hidden md:inline text-sm font-medium capitalize">{user?.full_name?.split(" ")[0] || role}</span>
        </button>
        {openUser && (
          <div className="absolute right-0 top-12 w-56 rounded-xl border border-[var(--border)] bg-[var(--card)] shadow-[var(--shadow-elevated)] z-50 overflow-hidden animate-[slideUp_0.2s_ease-out]" role="menu">
            <div className="px-3 py-3 border-b border-[var(--border)]">
              <div className="text-sm font-semibold truncate">{user?.full_name || "—"}</div>
              <div className="text-xs text-[var(--muted-foreground)] truncate">{user?.email}</div>
              <div className="mt-2 inline-flex items-center gap-1 text-[10px] font-semibold uppercase tracking-wider rounded-full bg-brand-500/15 text-brand-600 px-2 py-0.5">
                {role}
              </div>
            </div>
            <div className="py-1">
              <button onClick={() => { navigate("/profile"); setOpenUser(false); }} className="w-full text-left px-3 py-2 text-sm hover:bg-[var(--accent)] flex items-center gap-2" role="menuitem">
                <UserIcon className="h-4 w-4" /> Profile
              </button>
              <button onClick={() => { navigate("/settings"); setOpenUser(false); }} className="w-full text-left px-3 py-2 text-sm hover:bg-[var(--accent)] flex items-center gap-2" role="menuitem">
                <SettingsIcon className="h-4 w-4" /> Settings
              </button>
              <div className="my-1 border-t border-[var(--border)]" />
              <button onClick={handleLogout} className="w-full text-left px-3 py-2 text-sm hover:bg-[var(--accent)] flex items-center gap-2 text-[var(--error)]" role="menuitem">
                <LogOut className="h-4 w-4" /> Sign out
              </button>
            </div>
          </div>
        )}
      </div>
    </header>
  );
}
