import { NavLink } from "react-router-dom";
import { ChevronsLeft, ChevronsRight } from "lucide-react";
import { NAV } from "@/lib/nav";
import { useAuth } from "@/store/auth";
import { cn, initials } from "@/lib/utils";
import { Logo } from "@/components/common/Logo";

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  mobileOpen?: boolean;
  onMobileClose?: () => void;
}

export function Sidebar({ collapsed, onToggle, mobileOpen, onMobileClose }: SidebarProps) {
  const user = useAuth((s) => s.user);
  const role = user?.role || "student";
  const sections = NAV[role] || NAV.student;

  return (
    <>
      {mobileOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/50 backdrop-blur-sm z-40 animate-[fadeIn_0.2s_ease-out]"
          onClick={onMobileClose}
        />
      )}
      <aside
        className={cn(
          "fixed lg:sticky top-0 left-0 z-50 h-dvh flex flex-col bg-[var(--card)] border-r border-[var(--border)]",
          "transition-[width,transform] duration-200 ease-out",
          collapsed ? "w-[68px]" : "w-64",
          "lg:translate-x-0",
          mobileOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        )}
      >
        <div className="h-16 flex items-center justify-between px-4 border-b border-[var(--border)] shrink-0">
          <Logo size="md" withWordmark={!collapsed} />
          <button
            onClick={onToggle}
            className="hidden lg:flex h-7 w-7 rounded-md items-center justify-center text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] transition-colors"
            aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          >
            {collapsed ? <ChevronsRight className="h-4 w-4" /> : <ChevronsLeft className="h-4 w-4" />}
          </button>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {sections.map((sec) => (
            <div key={sec.section} className="mb-3">
              {!collapsed && (
                <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-[var(--muted-foreground)]">
                  {sec.section}
                </div>
              )}
              <div className="space-y-0.5">
                {sec.items?.map((item) => (
                  <NavLink
                    key={item.id}
                    to={`/${item.id}`}
                    onClick={onMobileClose}
                    className={({ isActive }) =>
                      cn(
                        "group flex items-center gap-3 rounded-lg text-sm font-medium transition-all relative",
                        collapsed ? "h-10 w-10 mx-auto justify-center" : "h-9 px-3",
                        isActive
                          ? "bg-brand-500/10 text-brand-600 dark:text-brand-400"
                          : "text-[var(--muted-foreground)] hover:bg-[var(--accent)] hover:text-[var(--foreground)]"
                      )
                    }
                    title={collapsed ? item.label : undefined}
                  >
                    {({ isActive }) => (
                      <>
                        {isActive && !collapsed && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 h-5 w-1 rounded-r-full bg-brand-500" />
                        )}
                        <item.icon className={cn("shrink-0", collapsed ? "h-5 w-5" : "h-4 w-4")} />
                        {!collapsed && <span className="flex-1 truncate">{item.label}</span>}
                        {!collapsed && item.badge != null && item.badge > 0 && (
                          <span className="text-[10px] font-bold bg-[var(--error)] text-[var(--error-fg)] rounded-full px-1.5 min-w-[18px] text-center">
                            {item.badge}
                          </span>
                        )}
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div className="p-3 border-t border-[var(--border)] shrink-0">
          <div className={cn("flex items-center gap-3", collapsed ? "justify-center" : "")}>
            <div className="h-9 w-9 rounded-full bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center text-white text-sm font-semibold shrink-0">
              {initials(user?.full_name)}
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold truncate">{user?.full_name || "—"}</div>
                <div className="text-xs text-[var(--muted-foreground)] capitalize">{role}</div>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}
